from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal


class GenerateRequest(BaseModel):
    """ Запрос на генерацию вариантов заданий.    
    Используется в эндпоинте: POST /generate
    """
    session_id: str
    original_text: Optional[str] = None  # может быть None, если текст загружен через файл
    num_variants: int = Field(default=4, ge=2, le=10)  # по кейсу: от 2 до 10
    variation_types: List[str] = Field(
        default_factory=lambda: ["numbers", "order"]
    )
    forbidden_parts: Optional[str] = None
    difficulty_override: Optional[str] = None  # "easier", "same", "harder"
    target_grade: Optional[str] = None  # "5", "6", "7", "8", "9", "10", "11"


class EditVariantRequest(BaseModel):
    """Запрос на редактирование варианта.
    Используется в эндпоинте: POST /edit-variant
    """
    session_id: str
    task_id: int
    variant_number: int = Field(ge=1)
    edited_content: str


class ExportRequest(BaseModel):
    """Запрос на экспорт в PDF или DOCX.
    Используется в эндпоинте: POST /export
    """
    session_id: str
    task_id: int
    format: Literal["pdf", "docx"]  # только эти два формата


class RegenerateVariantRequest(BaseModel):
    """Запрос на перегенерацию одного варианта.
    Используется в эндпоинте: POST /regenerate-variant
    """
    session_id: str
    task_id: int
    variant_number: int = Field(ge=1)


class AnalyzeTaskRequest(BaseModel):
    """Запрос на анализ структуры задания.
    Используется в эндпоинте: POST /analyze
    """
    session_id: str
    text: str  # текст для анализа


class ValidateVariantsRequest(BaseModel):
    """Запрос на валидацию сгенерированных вариантов.
    Используется в эндпоинте: POST /validate
    """
    session_id: str
    task_id: int
    variants: Dict[int, str]  # {1: "текст", 2: "текст"}
    original_text: str


class TaskStructureResponse(BaseModel):
    """Ответ после анализа структуры задания.
    Соответствует возвращаемым данным из analyze_task_structure().
    """
    subject: str
    task_type: str
    difficulty_score: int
    operations_count: int
    grade: str
    variable_elements: List[str]
    invariant_elements: List[str]
    recommended_variations: List[str]
    why_difficulty: str
    why_invariant: str
    why_variable: str


class GenerateResponse(BaseModel):
    """Ответ после генерации вариантов.
    """
    task_id: int
    variants: Dict[int, str]
    task_structure: Optional[Dict] = None
    validation: Optional[Dict] = None
    message: str