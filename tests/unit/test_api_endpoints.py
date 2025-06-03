# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io

from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_services():
    with patch('app.main.extract_text_from_file') as mock_extract, \
         patch('app.main.generate_summary') as mock_summarize, \
         patch('app.main.find_best_match') as mock_match, \
         patch('app.main.log_request') as mock_log:
        
        mock_extract.return_value = ("mocked_cv.pdf", "Texto extraído do CV mockado.")
        mock_summarize.return_value = "Este é um sumário mockado do serviço."
        mock_match.return_value = {
            "file_name": "mocked_cv.pdf",
            "justification": "Match mockado pelo serviço."
        }
        
        yield mock_extract, mock_summarize, mock_match, mock_log


def test_process_resumes_summarization_success():
    fake_pdf_content = b"dummy pdf content"
    files = {'files': ('test_cv.pdf', io.BytesIO(fake_pdf_content), 'application/pdf')}
    
    data = {
        'request_id': 'req-sum-001',
        'user_id': 'user-sum-test'
    }
    
    response = client.post("/process-resumes", data=data, files=files)
    
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["request_id"] == "req-sum-001"
    assert len(json_response["summaries"]) == 1
    assert json_response["summaries"][0]["file_name"] == "mocked_cv.pdf" # Veio do mock_extract
    assert "sumário mockado do serviço" in json_response["summaries"][0]["summary"] # Veio do mock_summarize

    # Verificar se o log_request foi chamado (usando o mock da fixture)
    # Acessar o mock_log de alguma forma, pode ser pegando da fixture se precisar
    # Neste exemplo, a fixture já fez o patch, então o serviço de log real não foi chamado.
    # Para verificar chamadas, o mock precisa ser acessível.
    # Uma forma é não usar autouse e passar a fixture como argumento:
    # def test_process_resumes_summarization_success(mock_services):
    #     _, _, _, mock_log_func = mock_services
    #     ...
    #     mock_log_func.assert_called_once()


def test_process_resumes_matching_success():
    fake_png_content = b"dummy png content"
    files = {'files': ('test_cv.png', io.BytesIO(fake_png_content), 'image/png')}
    
    data = {
        'request_id': 'req-match-002',
        'user_id': 'user-match-test',
        'query': 'Engenheiro de Testes'
    }
    
    response = client.post("/process-resumes", data=data, files=files)
    
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["request_id"] == "req-match-002"
    assert json_response["best_match"]["file_name"] == "mocked_cv.pdf" # Veio do mock_extract
    assert "Match mockado pelo serviço" in json_response["best_match"]["justification"]


def test_process_resumes_no_files_error():
    data = {
        'request_id': 'req-err-003',
        'user_id': 'user-err-test'
    }
    # Não envia 'files'
    response = client.post("/process-resumes", data=data)
    # FastAPI/Starlette retorna 422 para campos de formulário faltando que são obrigatórios
    # Se a lógica interna do endpoint for alcançada e 'files' estiver vazio, pode ser 400.
    # No caso de `List[UploadFile] = File(...)`, se nenhum arquivo é enviado,
    # a validação do FastAPI/Pydantic deve pegar isso.
    # Mas, se a lista de arquivos for opcional e vazia, aí sua lógica interna de 400 seria ativada.
    # Como 'files' é obrigatório (File(...)), um erro 422 Unprocessable Entity é esperado.
    assert response.status_code == 422 # Ou 400 se sua lógica específica tratar isso

# Adicione mais testes para:
# - Múltiplos arquivos
# - Tipos de arquivo inválidos (verificar como seu endpoint trata isso)
# - Query vazia (deve ir para sumarização)
# - Falhas nos serviços mockados (ex: mock_extract levanta uma exceção)