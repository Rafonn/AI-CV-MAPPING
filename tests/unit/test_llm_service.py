# tests/unit/test_llm_service.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.llm_service import generate_summary, find_best_match

@patch('app.services.llm_service.summarizer')
def test_generate_summary_success(mock_summarizer_pipeline):
    mock_summarizer_pipeline.return_value = [{"summary_text": "Este é um sumário mockado."}]

    with patch('app.services.llm_service.summarizer.model.generate', return_value=MagicMock()) as mock_generate, \
         patch('app.services.llm_service.summarizer.tokenizer.decode', return_value="Este é um sumário mockado.") as mock_decode, \
         patch('app.services.llm_service.summarizer.tokenizer') as mock_tokenizer_obj: # para model_max_length
        
        mock_tokenizer_obj.model_max_length = 512 # Exemplo
        mock_tokenizer_obj.return_value = {"input_ids": MagicMock()} # Mock da saída do tokenizer(text,...)

        text_input = "Texto longo para ser sumarizado."
        summary = generate_summary(text_input)
        assert summary == "Este é um sumário mockado."
        mock_generate.assert_called()
        mock_decode.assert_called()

@patch('app.services.llm_service.text_generator')
def test_find_best_match_success(mock_text_generator_pipeline):
    mock_text_generator_pipeline.return_value = [{
        "generated_text": "ARQUIVO: cv1.pdf JUSTIFICATIVA: Candidato excelente."
    }]
    
    query_jd = "Vaga para Dev Python"
    resume_data = [{"file_name": "cv1.pdf", "text": "Dev Python com 5 anos exp."},
                   {"file_name": "cv2.pdf", "text": "Dev Java com 3 anos exp."}]
    
    match = find_best_match(query_jd, resume_data)
    
    assert match is not None
    assert match["file_name"] == "cv1.pdf"
    assert "Candidato excelente" in match["justification"]
    mock_text_generator_pipeline.assert_called_once()