import re
import logging
from typing import List, Union
from document_models import TextBlock, FormulaBlock, TableBlock, VariantDocument

logger = logging.getLogger(__name__)

LATEX_PATTERN = re.compile(
    r'\\\((.+?)\\\)|\\\[(.+?)\\\]',
    re.DOTALL
)

# 
TABLE_PATTERN = re.compile(
    r'\\begin\{(?:array|tabular)\}.*?\\end\{(?:array|tabular)\}',
    re.DOTALL
)

def repair_latex_tables(text: str) -> str:
    """ Чинит незакрытые LaTeX array таблицы """
    # Если есть begin{array}, но нет end{array}
    if r'\begin{array}' in text and r'\end{array}' not in text:
        logger.warning("⚠️ Найдена незакрытая таблица LaTeX, пытаемся починить")
        
        # Вариант 1: вставляем end{array} перед ]
        if ']' in text:
            text = text.replace(
                r']',
                r'\end{array}' + '\n' + r']',
                1
            )
        # Вариант 2: вставляем перед \]
        elif r'\]' in text:
            text = text.replace(
                r'\]',
                r'\end{array}' + '\n' + r'\]',
                1
            )
        # Вариант 3: просто добавляем в конец
        else:
            text = text + r'\end{array}'
        
        logger.info("✅ Таблица починена")
    
    return text

def parse_latex_table(latex: str) -> tuple[List[str], List[List[str]]]:
    """Парсит LaTeX таблицу в заголовки и строки"""
    try:
        patterns = [
            r'\\begin\{array\}\{.*?\}(.*?)\\end\{array\}',
            r'\\begin\{tabular\}\{.*?\}(.*?)\\end\{tabular\}',
        ]
        
        content = None
        for pattern in patterns:
            match = re.search(pattern, latex, re.DOTALL)
            if match:
                content = match.group(1)
                break
        
        if not content:
            return [], []
        
        rows_data = []
        
        # Разбиваем по строкам, учитывая \hline
        for row in content.split(r'\\'):
            row = row.strip()
            
            # Убираем \hline и другие горизонтальные линии
            row = re.sub(r'\\hline', '', row)
            row = row.strip()
            
            if not row:
                continue
            
            # Извлекаем ячейки
            cells = []
            for cell in row.split('&'):
                cell = cell.strip()
                # Убираем LaTeX команды
                cell = re.sub(r'\\text\{(.*?)\}', r'\1', cell)
                cell = re.sub(r'\\textbf\{(.*?)\}', r'\1', cell)
                cell = re.sub(r'\\textit\{(.*?)\}', r'\1', cell)
                cell = cell.strip()
                cells.append(cell)
            
            if cells:
                rows_data.append(cells)
        
        if not rows_data:
            return [], []
        
        headers = rows_data[0] if rows_data else []
        rows = rows_data[1:] if len(rows_data) > 1 else []
        
        return headers, rows
        
    except Exception as e:
        logger.warning(f"Ошибка парсинга таблицы: {e}")
        return [], []

def parse_variant_to_document(text: str, number: int) -> VariantDocument:
    """Превращает текст с LaTeX в структурированный документ"""
    
    text = repair_latex_tables(text)
    
    blocks = []
    last_end = 0
    
    table_matches = list(TABLE_PATTERN.finditer(text))
    
    if table_matches:
        current_pos = 0
        for match in table_matches:
            start, end = match.span()
            
            if start > current_pos:
                plain_text = text[current_pos:start]
                if plain_text.strip():
                    blocks.extend(parse_text_with_formulas(plain_text))
            
            # Парсим таблицу
            table_latex = match.group(0)
            headers, rows = parse_latex_table(table_latex)
            
            if headers: 
                blocks.append(TableBlock(table_latex, headers, rows))
                logger.info(f"Найдена таблица: {len(headers)} колонок, {len(rows)} строк")
            else:
                blocks.append(TextBlock(table_latex))
                logger.warning(f"Не удалось распарсить таблицу, сохранена как текст")
            
            current_pos = end
        
        if current_pos < len(text):
            tail = text[current_pos:]
            if tail.strip():
                blocks.extend(parse_text_with_formulas(tail))
    else:
        blocks.extend(parse_text_with_formulas(text))
    
    return VariantDocument(number=number, blocks=blocks)


def parse_text_with_formulas(text: str) -> List[Union[TextBlock, FormulaBlock]]:
    """Парсит текст, сохраняя переносы строк"""
    blocks = []
    
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        
        last_end = 0
        paragraph_blocks = []
        
        for match in LATEX_PATTERN.finditer(paragraph):
            start, end = match.span()
            
            if start > last_end:
                plain_text = paragraph[last_end:start]
                if plain_text.strip():
                    paragraph_blocks.append(TextBlock(plain_text))
            
            latex = match.group(1) or match.group(2)
            if latex and latex.strip():
                paragraph_blocks.append(FormulaBlock(latex.strip()))
            
            last_end = end
        
        if last_end < len(paragraph):
            tail = paragraph[last_end:]
            if tail.strip():
                paragraph_blocks.append(TextBlock(tail))
        
        if not paragraph_blocks:
            blocks.append(TextBlock(paragraph.strip()))
        else:
            blocks.extend(paragraph_blocks)
        
        blocks.append(TextBlock('\n')) 
    
    return blocks