import io
import logging
import textwrap
from datetime import datetime
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from docx import Document as DocxDocument
from docx.shared import Pt

# Логирование
logger = logging.getLogger(__name__)

# Константы
FONT_NAME = "DejaVu"
FONT_PATH = "fonts/DejaVuSans.ttf"

# Регистрация шрифта
FONT_AVAILABLE = False
try:
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
    FONT_AVAILABLE = True
    logger.info("Шрифт DejaVu загружен, PDF будет с кириллицей")
except Exception as e:
    logger.warning(f"Шрифт не найден: {FONT_PATH}. PDF экспорт будет недоступен. Ошибка: {e}")


def export_to_pdf(variants: List[str]) -> io.BytesIO:
    """ Экспорт вариантов в PDF с поддержкой кириллицы """
    if not FONT_AVAILABLE:
        raise RuntimeError(
            "PDF экспорт недоступен: шрифт DejaVuSans.ttf не найден. "
        )
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Метаданные
    c.setTitle("TaskForge AI - Варианты заданий")
    c.setAuthor("TaskForge AI")
    
    # Текущая позиция
    y = height - 50
    current_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Шапка с датой 
    c.setFont(FONT_NAME, 9)
    c.drawRightString(width - 50, height - 30, f"Сгенерировано: {current_date}")
    c.setFont(FONT_NAME, 10)
    
    for i, variant in enumerate(variants, start=1):
        # Проверка места на странице
        if y < 100:
            c.showPage()
            y = height - 50
            c.setFont(FONT_NAME, 9)
            c.drawRightString(width - 50, height - 30, f"Сгенерировано: {current_date}")
            c.setFont(FONT_NAME, 10)
        
        # Заголовок варианта
        c.setFont(FONT_NAME, 14)
        c.drawString(50, y, f"ВАРИАНТ {i}")
        y -= 20
        
        # Разделительная линия
        c.line(50, y + 5, width - 50, y + 5)
        y -= 15
        
        # Основной текст
        c.setFont(FONT_NAME, 10)
        
        # Разбиваем на строки
        lines = variant.split('\n')
        for line in lines:
            if not line.strip():
                y -= 8
                continue
            
            # Перенос длинных строк
            wrapped_lines = textwrap.wrap(line, width=85)
            for wrapped_line in wrapped_lines:
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont(FONT_NAME, 9)
                    c.drawRightString(width - 50, height - 30, f"Сгенерировано: {current_date}")
                    c.setFont(FONT_NAME, 10)
                
                c.drawString(50, y, wrapped_line)
                y -= 13
        
        # Отступ между вариантами
        y -= 20
    
    c.save()
    buffer.seek(0)
    return buffer


def export_to_docx(variants: List[str]) -> io.BytesIO:
    """ Экспорт вариантов в DOCX с форматированием """
    doc = DocxDocument()
    
    # Заголовок документа
    doc.add_heading("TaskForge AI", 0)
    
    # Дата
    date_para = doc.add_paragraph()
    date_para.add_run(f"Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    
    doc.add_paragraph()
    
    for i, variant in enumerate(variants, start=1):
        # Заголовок варианта
        doc.add_heading(f"ВАРИАНТ {i}", level=1)
        
        # Основной текст
        para = doc.add_paragraph()
        run = para.add_run(variant)
        run.font.size = Pt(11)
        
        # Разрыв страницы между вариантами (кроме последнего)
        if i < len(variants):
            doc.add_page_break()
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer