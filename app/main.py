# app/main.py

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from typing import List, Optional, Union, Dict, Any
from uuid import uuid4, UUID
import datetime

from .models.schemas import (
    ResumeSummary,
    QueryMatch,
    SummaryResponse,
    QueryResponse,
    LogEntry
)

from .services import (
    extract_text_from_file, # do ocr_service
    generate_summary,       # do llm_service
    find_best_match,        # do llm_service
    log_request             # do db_service
)

from .core.config import settings

app = FastAPI(
    title="Serviço Inteligente de Triagem de Currículos de Fabio",
    version="1.0.0",
    description="""
    API para extrair texto de currículos (PDF/imagem), gerar sumários
    e encontrar o melhor candidato para uma vaga específica.
    """,
)

# --- Endpoints da API ---

@app.post(
    "/process-resumes",
    response_model=Union[SummaryResponse, QueryResponse],
    summary="Processa currículos para sumarização ou matching com vaga",
    tags=["Currículos"],
    responses={
        200: {
            "description": "Processamento bem-sucedido.",
            "content": {
                "application/json": {
                    "examples": {
                        "summaries_only": {
                            "summary": "Retorno com sumários individuais",
                            "value": {
                                "request_id": "some-uuid-123",
                                "summaries": [
                                    {"file_name": "cv1.pdf", "summary": "Sumário do CV 1..."},
                                    {"file_name": "cv2.jpg", "summary": "Sumário do CV 2..."}
                                ]
                            }
                        },
                        "query_match": {
                            "summary": "Retorno com o melhor match para a query",
                            "value": {
                                "request_id": "another-uuid-456",
                                "best_match": {
                                    "file_name": "cv1.pdf",
                                    "justification": "Este candidato é ideal porque..."
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {"description": "Erro na requisição (ex: request_id faltando)"},
        422: {"description": "Erro de validação (ex: tipo de arquivo inválido não enviado no form, mas FastAPI pode pegar antes)"},
        500: {"description": "Erro interno no processamento"},
    }
)
async def process_resumes_endpoint(
    request_id: str = Form(..., example=str(uuid4()), description="ID único para esta requisição (UUID recomendado)."),
    user_id: str = Form(..., example="fabio_rh_123", description="Identificador do usuário solicitante."),
    query: Optional[str] = Form(None, example="Engenheiro de Software Pleno, Python, FastAPI, AWS", description="Descrição da vaga e requisitos (opcional). Se não informado, retorna sumários."),
    files: List[UploadFile] = File(..., description="Lista de arquivos de currículo (PDF, JPG, PNG).")
):
    """
    Recebe múltiplos arquivos de currículo (PDFs ou imagens), extrai o texto,
    e realiza uma das seguintes ações:

    1.  Se query NÃO for informado: Gera e retorna um sumário individual para cada currículo.
    2.  Se query FOR informado: Analisa os currículos em relação à query (descrição da vaga)
        e retorna o currículo mais adequado com uma justificativa.

    Todos os usos são registrados para auditoria.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    extracted_texts_data = []
    processing_errors = []

    for file in files:
        if not file.filename:
            processing_errors.append({"file_name": "desconhecido", "error": "Arquivo sem nome."})
            continue
        if not file.content_type in ["application/pdf", "image/jpeg", "image/png"]:
            processing_errors.append({"file_name": file.filename, "error": f"Tipo de arquivo não suportado: {file.content_type}"})
            continue
        try:
            file_name, text = await extract_text_from_file(file)
            if not text.strip() and not f"[ERRO: Tipo de arquivo {file.content_type} não suportado" in text:
                 processing_errors.append({"file_name": file_name, "error": "OCR não conseguiu extrair texto ou o arquivo está vazio."})

                 # Mesmo com erro de OCR, continua e loga o que foi possível
                 extracted_texts_data.append({"file_name": file_name, "text": "", "original_content_type": file.content_type})
            else:
                extracted_texts_data.append({"file_name": file_name, "text": text, "original_content_type": file.content_type})
        except Exception as e:
            processing_errors.append({"file_name": file.filename, "error": f"Erro crítico ao processar arquivo: {str(e)}"})
            extracted_texts_data.append({"file_name": file.filename, "text": "", "error": str(e), "original_content_type": file.content_type})


    # Se houve erros em todos os arquivos e nenhum texto foi extraído
    if not any(item.get("text") for item in extracted_texts_data) and processing_errors:
        error_detail_str = "; ".join([f"{e['file_name']}: {e['error']}" for e in processing_errors])
        log_request(
            request_id=request_id,
            user_id=user_id,
            query=query,
            result={"message": "Falha ao processar todos os arquivos.", "errors": processing_errors},
            error=f"Falha no processamento de todos os arquivos: {error_detail_str}"
        )
        raise HTTPException(status_code=500, detail=f"Não foi possível processar nenhum dos arquivos. Erros: {processing_errors}")

    # Filtrar apenas os que tiveram texto extraído para LLM
    valid_texts_for_llm = [data for data in extracted_texts_data if data.get("text","").strip()]

    final_response_data: Dict[str, Any]
    log_result_data: Dict[str, Any]

    if query:
        # Modo de matching com a vaga
        if not valid_texts_for_llm:
            match_result = {"file_name": "Nenhum currículo válido para análise", "justification": "Nenhum texto pôde ser extraído dos arquivos fornecidos."}
        else:
            match_result = find_best_match(query_jd=query, resume_data=valid_texts_for_llm)

        response_payload = QueryResponse(request_id=request_id, best_match=match_result)
        final_response_data = response_payload.model_dump() # Pydantic v2
        log_result_data = {"best_match": match_result, "processing_errors": processing_errors if processing_errors else None}

    else:
        # Modo de sumarização
        summaries = []
        if not valid_texts_for_llm:
             summaries.append(ResumeSummary(file_name="Nenhum currículo válido", summary="Nenhum texto pôde ser extraído dos arquivos fornecidos."))
        else:
            for item_data in valid_texts_for_llm:
                summary_text = generate_summary(text=item_data["text"])
                summaries.append(ResumeSummary(file_name=item_data["file_name"], summary=summary_text))
        for err_item in processing_errors:
            if not any(s.file_name == err_item["file_name"] for s in summaries):
                 summaries.append(ResumeSummary(file_name=err_item["file_name"], summary=f"Falha no processamento: {err_item['error']}"))


        response_payload = SummaryResponse(request_id=request_id, summaries=summaries)
        final_response_data = response_payload.model_dump() # Pydantic v2
        log_result_data = {"summaries": [s.model_dump() for s in summaries], "processing_errors": processing_errors if processing_errors else None}

    # Registrar no log
    log_request(
        request_id=request_id,
        user_id=user_id,
        query=query,
        result=log_result_data,
        error=None
    )

    return final_response_data

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)