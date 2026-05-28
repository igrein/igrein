from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class AnswerFormat(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_SELECT = "multi_select"
    NUMBER = "number"
    FORMULA = "formula"
    TEXT = "text"
    BOOLEAN = "boolean"


class StructuralType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    MATCHING = "matching"
    ORDERING = "ordering"
    CLASSIFICATION = "classification"
    FILL_BLANKS = "fill_blanks"
    OPEN_RESPONSE = "open_response"
    CALCULATION = "calculation"
    PROOF = "proof"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    # Алиасы
    CLASSIFICATION_STRUCT = "classification"
    PROOF_STRUCT = "proof"


@dataclass
class ValidationResult:
    correct: bool
    confidence: float
    normalized_answer: str
    expected_answer: str
    error_message: Optional[str] = None


class BaseValidator:
    def normalize(self, text: str) -> str:
        if not text:
            return ""
        return str(text).strip().lower()


class TextValidator(BaseValidator):
    def validate(self, answer: str, expected: str, context: Dict = None) -> ValidationResult:
        norm_answer = self.normalize(answer)
        norm_expected = self.normalize(expected)
        is_correct = norm_answer == norm_expected
        return ValidationResult(
            correct=is_correct,
            confidence=1.0 if is_correct else 0.0,
            normalized_answer=norm_answer,
            expected_answer=norm_expected
        )


def validate_answers_batch(
    answers: Dict[int, str],
    expected_answers: Dict[int, str],
    subject: Optional[str] = None,
    answer_format: Optional[AnswerFormat] = None,
    structural_type: Optional[StructuralType] = None,
    context: Optional[Dict] = None
) -> Dict[int, ValidationResult]:
    """Простая валидация - сравнение строк"""
    validator = TextValidator()
    results = {}
    
    for num, answer in answers.items():
        expected = expected_answers.get(num, "")
        if not expected:
            results[num] = ValidationResult(
                correct=False,
                confidence=0.0,
                normalized_answer=str(answer),
                expected_answer="",
                error_message="Нет ожидаемого ответа"
            )
        else:
            results[num] = validator.validate(str(answer), str(expected), context)
    
    return results


def format_validation_for_frontend(results: Dict[int, ValidationResult]) -> Dict[str, Any]:
    variant_status = {}
    answers_display = {}
    
    for num, result in results.items():
        num_str = str(num)
        variant_status[num_str] = {
            "valid": result.correct,
            "solvable": True,
            "same_topic": True,
            "same_structure": True,
            "issues": [] if result.correct else [f"Неверный ответ. Ожидалось: {result.expected_answer}"],
            "confidence": result.confidence
        }
        answers_display[num_str] = result.normalized_answer
    
    return {
        "valid": all(r.correct for r in results.values()),
        "variant_status": variant_status,
        "answers": answers_display,
        "summary": {
            "total": len(results),
            "valid_count": sum(1 for r in results.values() if r.correct),
            "invalid_count": sum(1 for r in results.values() if not r.correct)
        }
    }


def detect_structural_type_from_text(text: str) -> Optional[StructuralType]:
    text_lower = text.lower()
    if any(w in text_lower for w in ["выбери", "укажите", "выберите"]):
        return StructuralType.MULTIPLE_CHOICE
    if any(w in text_lower for w in ["соотнеси", "сопоставь"]):
        return StructuralType.MATCHING
    if any(w in text_lower for w in ["вставь", "пропуск", "заполни", "___"]):
        return StructuralType.FILL_BLANKS
    if any(w in text_lower for w in ["вычисли", "найди", "реши"]):
        return StructuralType.CALCULATION
    return None


def get_answer_format_instruction(structural_type: StructuralType) -> str:
    instructions = {
        StructuralType.MULTIPLE_CHOICE: "Верни буквы правильных вариантов через запятую",
        StructuralType.MATCHING: "Верни пары через запятую, используя дефис",
        StructuralType.FILL_BLANKS: "Верни вставленные слова через запятую",
        StructuralType.CALCULATION: "Верни число или формулу",
        StructuralType.OPEN_RESPONSE: "Верни краткий ответ",
    }
    return instructions.get(structural_type, "Верни краткий ответ")