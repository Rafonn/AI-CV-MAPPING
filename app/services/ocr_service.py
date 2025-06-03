import easyocr
from PIL import Image
import fitz # PyMuPDF
import io

try:
    reader = easyocr.Reader(['pt', 'en'])
except Exception as e:
    print(f"Erro ao inicializar EasyOCR: {e}. Verifique as dependências (PyTorch, etc.).")
    reader = None

def extract_text_from_image(image_bytes: bytes) -> str:
    if not reader:
        raise RuntimeError("EasyOCR reader não foi inicializado.")
    try:
        image = Image.open(io.BytesIO(image_bytes))
        result = reader.readtext(image_bytes)
        text = " ".join([item[1] for item in result])
        return text
    except Exception as e:
        print(f"Erro ao processar imagem com EasyOCR: {e}")
        return ""

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    full_text = ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            text = page.get_text("text")
            if not text.strip() and reader:
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                text = extract_text_from_image(img_bytes)
            full_text += text + "\n"
        doc.close()
        return full_text.strip()
    except Exception as e:
        print(f"Erro ao processar PDF: {e}")
        return ""

async def extract_text_from_file(file) -> tuple[str, str]:
    contents = await file.read()
    file_name = file.filename
    text = ""
    if file.content_type == "application/pdf":
        text = extract_text_from_pdf(contents)
    elif file.content_type in ["image/jpeg", "image/png"]:
        text = extract_text_from_image(contents)
    else:
        print(f"Tipo de arquivo não suportado: {file.content_type} para {file_name}")
        text = f"[ERRO: Tipo de arquivo {file.content_type} não suportado para {file_name}]"
    return file_name, text