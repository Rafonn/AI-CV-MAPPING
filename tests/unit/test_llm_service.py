# tests/unit/test_llm_service.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.llm_service import generate_summary, find_best_match

@patch('app.services.llm_service.summarizer')
def test_generate_summary_success(mock_summarizer_pipeline):
    mock_summarizer_pipeline.return_value = [{"summary_text": "Este é um sumário mockado."}]
    # Se o seu pipeline for chamado diretamente (ex: summarizer(text_input, ...))
    # E se você estiver usando o método .generate() diretamente no modelo:
    # mock_summarizer_model = MagicMock()
    # mock_summarizer_model.generate.return_value = tokenizer.encode("Este é um sumário mockado.", return_tensors="pt")
    # mock_summarizer_tokenizer = MagicMock()
    # mock_summarizer_tokenizer.decode.return_value = "Este é um sumário mockado."
    # # E então patchar o 'summarizer.model' e 'summarizer.tokenizer'

    # Simplificando, se 'summarizer' é o pipeline:
    # O pipeline pode retornar uma lista de dicts, ou um dict. Ajuste conforme a saída real.
    # A forma como você moca depende de como você usa o pipeline em llm_service.py
    # Se você fez: summary = summarizer(text_input, max_length=...)[0]['summary_text']
    
    # A forma como implementei o `generate_summary` no exemplo anterior usa `summarizer.model.generate`
    # e `summarizer.tokenizer.decode`. Vamos mocar esses.
    
    # Supondo que 'summarizer' é um objeto com 'model' e 'tokenizer'
    # e que 'llm_service.summarizer' se refere ao pipeline completo
    # Se 'summarizer' é o pipeline como em `pipeline("summarization", ...)`
    # e você chama `outputs = summarizer(text, ...)`
    
    # Se a implementação usa o objeto pipeline diretamente:
    # mock_summarizer_pipeline.return_value = [{'summary_text': 'Sumário mockado.'}]
    
    # Dada a implementação no exemplo anterior:
    # @patch('app.services.llm_service.summarizer_model.generate') # Se o modelo é global
    # @patch('app.services.llm_service.summarizer_tokenizer.decode') # Se o tokenizer é global

    # É mais fácil mocar o pipeline inteiro se ele é usado diretamente
    # Na minha implementação anterior, 'summarizer' é o pipeline.
    # A chamada é: summary_ids = summarizer.model.generate(...)
    # E: summary_text = summarizer.tokenizer.decode(...)
    # Então, é preciso mocar os atributos 'model' e 'tokenizer' do objeto 'summarizer' pipeline.
    
    # Mockando o pipeline inteiro, se a chamada fosse `summarizer(text, ...)`
    # mock_summarizer_pipeline.return_value = [{"summary_text": "Este é um sumário mockado."}]

    # Mockando os componentes internos do pipeline, conforme a implementação:
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