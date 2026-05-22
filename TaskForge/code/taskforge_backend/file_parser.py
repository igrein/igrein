import io
import re
from PyPDF2 import PdfReader
from docx import Document
import pytesseract
from PIL import Image


def parse_file(content: bytes, filename: str) -> str:
    """ Извлекает текст из файла """
    filename_lower = filename.lower()
    # TXT
    if filename_lower.endswith('.txt'):
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('cp1251')
        return _clean_text(text)
    # PDF
    elif filename_lower.endswith('.pdf'):
        try:
            reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if not text.strip():
                raise ValueError("PDF не содержит извлекаемого текста")
            return _clean_text(text)
        except Exception as e:
            raise ValueError(f"Ошибка чтения PDF: {str(e)}")
    # DOCX
    elif filename_lower.endswith('.docx'):
        try:
            doc = Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            if not paragraphs:
                raise ValueError("DOCX не содержит текста")
            return _clean_text("\n".join(paragraphs))
        except Exception as e:
            raise ValueError(f"Ошибка чтения DOCX: {str(e)}")
    # OCR
    elif filename_lower.endswith(('.png', '.jpg', '.jpeg')):
        try:
            image = Image.open(io.BytesIO(content))
            if image.mode not in ('L', 'RGB'):
                image = image.convert('RGB')
            try:
                text = pytesseract.image_to_string(image, lang='rus+eng')
            except Exception:
                raise ValueError(f"OCR недоступен: {str(e)}. Установите Tesseract.")
            if not text.strip():
                raise ValueError("Не удалось распознать текст на изображении")
            return _clean_text(text)
        except Exception as e:
            raise ValueError(f"Ошибка OCR: {str(e)}")
    
    else:
        raise ValueError(f"Неподдерживаемый формат: {filename}")


def _clean_text(text: str) -> str:
    """Очистка текста от мусора"""
    text = text.replace('\x00', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()