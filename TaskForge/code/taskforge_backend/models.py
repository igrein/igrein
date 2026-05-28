from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any


class EditVariantRequest(BaseModel):
    """Запрос на редактирование варианта.
    Используется в эндпоинте: POST /edit-variant
    """

    task_id: int
    variant_number: int = Field(ge=1)
    edited_content: str


class ExportRequest(BaseModel):
    """Запрос на экспорт в PDF или DOCX.
    Используется в эндпоинте: POST /export
    """
    task_id: int
    format: Literal["pdf", "docx"]  # только эти два формата


class RegenerateVariantRequest(BaseModel):
    """Запрос на перегенерацию одного варианта.
    Используется в эндпоинте: POST /regenerate-variant
    """
    task_id: int
    variant_number: int = Field(ge=1)


class AnalyzeTaskRequest(BaseModel):
    """Запрос на анализ структуры задания.
    Используется в эндпоинте: POST /analyze
    """
    text: str  # текст для анализа


class ValidateVariantsRequest(BaseModel):
    """Запрос на валидацию сгенерированных вариантов.
    Используется в эндпоинте: POST /validate
    """
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

class UserRegister(BaseModel):
    """Регистрация нового пользователя"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """Вход пользователя"""
    username: str
    password: str


class UserResponse(BaseModel):
    """Ответ с данными пользователя (без пароля)"""
    id: int
    username: str
    created_at: str


class TokenResponse(BaseModel):
    """Ответ с токеном сессии"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserInDB(UserResponse):
    """Внутреннее представление пользователя в БД"""
    password_hash: str


class VariantStatusItem(BaseModel):
    """Статус одного варианта при валидации"""
    valid: bool = Field(..., description="Прошёл ли вариант валидацию")
    issues: List[str] = Field(default_factory=list, description="Список проблем")
    difficulty_match: bool = Field(..., description="Сложность совпадает с эталоном")
    unique_answer: bool = Field(..., description="Ответ уникален среди вариантов")
    same_structure: bool = Field(..., description="Структура сохранена")
    solvable: bool = Field(..., description="Вариант имеет решение")


class VariantStatusResponse(BaseModel):
    """Детальный ответ валидации"""
    valid: bool = Field(..., description="Все ли варианты валидны")
    variant_status: Dict[str, VariantStatusItem] = Field(..., description="Статус по каждому варианту")
    answers: Dict[str, Optional[str]] = Field(..., description="Ответы для каждого варианта")
    summary: Dict[str, Any] = Field(..., description="Сводка по валидации")
    problems_remaining: Optional[Dict[str, List[str]]] = Field(None, description="Проблемы после всех итераций")








