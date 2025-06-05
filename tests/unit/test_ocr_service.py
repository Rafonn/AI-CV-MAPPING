# tests/unit/test_ocr_service.py
import pytest
from unittest.mock import patch, MagicMock
from app.services.ocr_service import extract_text_from_image, extract_text_from_pdf

@patch('app.services.ocr_service.reader')
def test_extract_text_from_image_success(mock_easyocr_reader):
    # Configura o mock para retornar um resultado esperado do EasyOCR
    mock_easyocr_reader.readtext.return_value = [
        (None, "Texto extraído da imagem.", None),
        (None, "Mais texto.", None)
    ]
    
    fake_image_bytes = b"dummyimagedata"
    text = extract_text_from_image(fake_image_bytes)
    
    assert "Texto extraído da imagem. Mais texto." in text
    mock_easyocr_reader.readtext.assert_called_once_with(fake_image_bytes)

@patch('app.services.ocr_service.reader')
def test_extract_text_from_image_ocr_failure(mock_easyocr_reader):
    mock_easyocr_reader.readtext.side_effect = Exception("OCR Falhou")
    
    fake_image_bytes = b"dummyimagedata"
    text = extract_text_from_image(fake_image_bytes)
    assert text == ""

@patch('app.services.ocr_service.fitz.open')
@patch('app.services.ocr_service.extract_text_from_image')
def test_extract_text_from_pdf_text_based(mock_extract_image, mock_fitz_open):
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Texto direto do PDF."
    
    mock_doc = MagicMock()
    mock_doc.load_page.return_value = mock_page
    mock_doc.__len__.return_value = 1 # PDF de 1 página
    
    mock_fitz_open.return_value = mock_doc
    
    fake_pdf_bytes = b"dummypdfdata"
    text = extract_text_from_pdf(fake_pdf_bytes)
    
    assert "Texto direto do PDF." in text
    mock_fitz_open.assert_called_once()
    mock_extract_image.assert_not_called()

@patch('app.services.ocr_service.fitz.open')
@patch('app.services.ocr_service.extract_text_from_image')
def test_extract_text_from_pdf_image_based(mock_extract_image, mock_fitz_open):
    mock_page = MagicMock()
    mock_page.get_text.return_value = ""
    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"imagedatafrompdfpage"
    mock_page.get_pixmap.return_value = mock_pixmap
    
    mock_doc = MagicMock()
    mock_doc.load_page.return_value = mock_page
    mock_doc.__len__.return_value = 1
    
    mock_fitz_open.return_value = mock_doc
    mock_extract_image.return_value = "Texto OCR da página do PDF."
    
    fake_pdf_bytes = b"dummypdfimagidata"
    text = extract_text_from_pdf(fake_pdf_bytes)
    
    assert "Texto OCR da página do PDF." in text
    mock_fitz_open.assert_called_once()
    mock_extract_image.assert_called_once_with(b"imagedatafrompdfpage")