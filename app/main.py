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
    LogEntry,
    ProcessingErrorDetail
)

from .services import (
    extract_text_from_file,
    generate_summary,
    find_best_match,
    log_request
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
                                "best_match": "CV e Justificativa"
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
                extracted_texts_data.append({"file_name": file_name, "text": "", "original_content_type": file.content_type})
            else:
                extracted_texts_data.append({"file_name": file_name, "text": text, "original_content_type": file.content_type})
        except Exception as e:
            error_msg = f"Erro crítico ao processar arquivo: {str(e)}"
            processing_errors.append({"file_name": file.filename, "error": error_msg})
            extracted_texts_data.append({"file_name": file.filename, "text": "", "error": str(e), "original_content_type": file.content_type})

    # Se houve erros em todos os arquivos e nenhum texto foi extraído
    if not any(item.get("text","").strip() for item in extracted_texts_data) and processing_errors:
        error_detail_str = "; ".join([f"{e['file_name']}: {e['error']}" for e in processing_errors])

        log_request(
            request_id=request_id,
            user_id=user_id,
            query=query,
            result={"message": "Falha ao processar todos os arquivos.", "errors": processing_errors},
            error=f"Falha no processamento de todos os arquivos: {error_detail_str}"
        )
        raise HTTPException(status_code=500, detail=f"Não foi possível processar nenhum dos arquivos. Erros: {processing_errors}")

    valid_texts_for_llm = [data for data in extracted_texts_data if data.get("text","").strip()]

    log_result_data_for_db: Dict[str, Any]
    response_payload: Union[SummaryResponse, QueryResponse]
    
    pydantic_processing_errors = [ProcessingErrorDetail(**err) for err in processing_errors] if processing_errors else None

    if query:
        match_output_from_llm: Union[Dict[str, Any], str]

        if not valid_texts_for_llm:
            match_output_from_llm = {
                "file_name": "Nenhum currículo válido para análise",
                "justification": "Nenhum texto pôde ser extraído dos arquivos fornecidos para a query."
            }
        else:
            match_output_from_llm = find_best_match(query_jd=query, resume_data=valid_texts_for_llm)

        log_result_data_for_db = {"best_match": match_output_from_llm, "processing_errors": processing_errors if processing_errors else None}

        api_best_match_data: Union[QueryMatch, str]
        if isinstance(match_output_from_llm, str):
            api_best_match_data = match_output_from_llm
        elif isinstance(match_output_from_llm, dict) and "file_name" in match_output_from_llm:
            try:
                api_best_match_data = QueryMatch(**match_output_from_llm)
            except Exception: 
                api_best_match_data = QueryMatch(
                    file_name=str(match_output_from_llm.get("file_name", "Output Inesperado")),
                    justification=str(match_output_from_llm)
                )
        else: 
             api_best_match_data = QueryMatch(file_name="Erro", justification="Formato de saída do LLM inesperado.")

        response_payload = QueryResponse(
            request_id=request_id,
            best_match=api_best_match_data,
            processing_errors=pydantic_processing_errors
        )

    else: # Modo de sumarização
        summaries_for_response: List[ResumeSummary] = []
        
        if not valid_texts_for_llm:
            # Se não há textos válidos, mas há arquivos processados com erro, informa isso.
            # Se não há nem arquivos processados, a verificação anterior de "extracted_texts_data" já teria pego.
            if not processing_errors and not extracted_texts_data: # Nenhum arquivo enviado ou todos sem nome/tipo
                 summaries_for_response.append(ResumeSummary(file_name="Nenhum arquivo processável", summary="Nenhum arquivo foi fornecido ou todos eram inválidos."))
            else:
                 summaries_for_response.append(ResumeSummary(file_name="Nenhum currículo válido para sumário", summary="Nenhum texto pôde ser extraído dos arquivos fornecidos."))
        else:
            for item_data in valid_texts_for_llm:
                summary_text = generate_summary(text=item_data["text"])
                summaries_for_response.append(ResumeSummary(file_name=item_data["file_name"], summary=summary_text))
        
        # Adiciona informações sobre arquivos que falharam no processamento e não estão já na lista de sumários
        processed_filenames_in_summaries = {s.file_name for s in summaries_for_response}
        if pydantic_processing_errors:
            for err_detail in pydantic_processing_errors:
                if err_detail.file_name not in processed_filenames_in_summaries:
                    summaries_for_response.append(ResumeSummary(file_name=err_detail.file_name, summary=f"Falha no processamento: {err_detail.error}"))
        
        log_result_data_for_db = {
            "summaries": [s.model_dump() for s in summaries_for_response],
            "processing_errors": processing_errors if processing_errors else None
        }

        response_payload = SummaryResponse(
            request_id=request_id,
            summaries=summaries_for_response,
            processing_errors=pydantic_processing_errors
        )

    log_request(
        request_id=request_id,
        user_id=user_id,
        query=query,
        result=log_result_data_for_db,
        error=None
    )

    return response_payload