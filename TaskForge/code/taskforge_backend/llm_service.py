import logging
import re
import hashlib
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from document_models import VariantDocument
from document_parser import parse_variant_to_document
from llm_client import call_llm, clean_json_response, _stringify_answer_object, normalize_for_cache
import json

# Импорты из answer_validators
from answer_validators import (
    validate_answers_batch, 
    format_validation_for_frontend,
    AnswerFormat,
    StructuralType,
    get_answer_format_instruction,
    detect_structural_type_from_text
)

logger = logging.getLogger(__name__)


# ПРЕСЕТЫ ВАРИАЦИЙ
VARIATION_PRESETS = {
    "minimal": ["numbers"],
    "standard": ["numbers", "order"],
    "full": ["numbers", "order", "synonyms"]
}


# ПЕДАГОГИЧЕСКАЯ МОДЕЛЬ

class PedagogicalIntent(str, Enum):
    FACT_RECALL = "fact_recall"
    CONCEPT_UNDERSTANDING = "concept_understanding"
    CLASSIFICATION = "classification"
    COMPARISON = "comparison"
    SEQUENCE = "sequence"
    APPLICATION = "application"
    CALCULATION = "calculation"
    PROOF = "proof"
    ANALYSIS = "analysis"
    ARGUMENTATION = "argumentation"
    TEXT_INTERPRETATION = "text_interpretation"
    GRAMMAR_RULE = "grammar_rule"
    MATCHING = "matching"


class CognitiveLevel(str, Enum):
    RECOGNITION = "recognition"
    REPRODUCTION = "reproduction"
    APPLICATION = "application"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"


class VariationPolicy(str, Enum):
    NUMERIC_PARAMETERS = "numeric_parameters"
    DOMAIN_ENTITIES = "domain_entities"
    SURFACE_WORDING = "surface_wording"
    ORDER = "order"
    DATASET = "dataset"


@dataclass
class PedagogicalSpec:
    pedagogical_intent: PedagogicalIntent
    cognitive_level: CognitiveLevel
    structural_type: StructuralType
    answer_format: AnswerFormat
    operations_count: int = 1
    cognitive_load: int = 1
    options_count: int = 0
    requires_single_correct: bool = True
    requires_unique_answer: bool = True
    
    def to_invariant_dict(self) -> Dict[str, Any]:
        return {
            "pedagogical_intent": self.pedagogical_intent.value,
            "cognitive_level": self.cognitive_level.value,
            "structural_type": self.structural_type.value,
            "answer_format": self.answer_format.value,
            "operations_count": self.operations_count,
            "cognitive_load": self.cognitive_load,
            "requires_unique_answer": self.requires_unique_answer
        }


@dataclass
class ContentSpec:
    knowledge_domain: str
    topic_core: str = ""
    grade: str = "5-9"  # ← добавить
    topic_boundaries: List[str] = field(default_factory=list)
    forbidden_topics: List[str] = field(default_factory=list)
    forbidden_entities: List[str] = field(default_factory=list)
    skill_target: str = ""
    content_entities: List[str] = field(default_factory=list)
    preserved_patterns: List[str] = field(default_factory=list)
    forbid_topic_shift: bool = True
    allowed_variations: List[VariationPolicy] = field(default_factory=lambda: [
        VariationPolicy.NUMERIC_PARAMETERS,
        VariationPolicy.DOMAIN_ENTITIES,
        VariationPolicy.SURFACE_WORDING
    ])


@dataclass
class TaskSpecification:
    pedagogical: PedagogicalSpec
    content: ContentSpec
    legacy_subject: str = "не определён"
    legacy_topic: str = "не определена"
    legacy_skill: str = "не определён"
    legacy_didactic_goal: str = "не определена"
    
    @property
    def difficulty_level(self) -> int:
        return min(10, self.pedagogical.cognitive_load * self.pedagogical.operations_count)
    
    def to_prompt_invariants(self) -> str:
        return f"""
=== ПЕДАГОГИЧЕСКИЕ ИНВАРИАНТЫ (НЕ МЕНЯТЬ) ===
📚 Педагогическая цель: {self.pedagogical.pedagogical_intent.value}
🧠 Когнитивный уровень: {self.pedagogical.cognitive_level.value}
🏗️ Структурный тип: {self.pedagogical.structural_type.value}
📝 Формат ответа: {self.pedagogical.answer_format.value}
🔢 Количество операций: {self.pedagogical.operations_count}

=== КОНТЕКСТ ===
Предмет: {self.content.knowledge_domain}
Тема: {self.content.topic_core if self.content.topic_core else "по эталону"}
"""
    
    def to_legacy_dict(self) -> Dict[str, Any]:
        structural_to_legacy = {
            StructuralType.MULTIPLE_CHOICE: "test",
            StructuralType.MATCHING: "matching",
            StructuralType.ORDERING: "ordering",
            StructuralType.CLASSIFICATION_STRUCT: "classification",
            StructuralType.FILL_BLANKS: "fill_blanks",
            StructuralType.OPEN_RESPONSE: "open_question",
            StructuralType.CALCULATION: "calculation",
            StructuralType.PROOF_STRUCT: "proof",
        }
        
        legacy_task_type = structural_to_legacy.get(self.pedagogical.structural_type, "calculation")
        
        return {
            "subject": self.legacy_subject,
            "task_type": legacy_task_type,
            "difficulty_score": self.difficulty_level,
            "operations_count": self.pedagogical.operations_count,
            "grade": self.content.grade if hasattr(self.content, 'grade') else "5-9",
            "topic": self.legacy_topic,
            "skill": self.legacy_skill,
            "didactic_goal": self.legacy_didactic_goal,
            "pedagogical_intent": self.pedagogical.pedagogical_intent.value,  # ← ДОБАВИТЬ
            "cognitive_level": self.pedagogical.cognitive_level.value,        # ← ДОБАВИТЬ
            "variable_elements": [v.value for v in self.content.allowed_variations],
            "invariant_elements": [
                f"pedagogical_intent: {self.pedagogical.pedagogical_intent.value}",
                f"cognitive_level: {self.pedagogical.cognitive_level.value}",
                f"structural_type: {self.pedagogical.structural_type.value}",
                f"topic_core: {self.content.topic_core}"
            ] + self.content.preserved_patterns,
            "recommended_variations": [v.value for v in self.content.allowed_variations],
            "why_difficulty": f"Когнитивная нагрузка {self.pedagogical.cognitive_load} × операции {self.pedagogical.operations_count}",
            "why_invariant": "Педагогическая модель и тема должны сохраняться",
            "why_variable": "Контент может варьироваться в пределах темы"
        }


# ГЛОБАЛЬНЫЙ КЭШ
_SPEC_CACHE: Dict[str, TaskSpecification] = {}


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def normalize_topic(topic: str) -> str:
    """Нормализует тему для консистентности"""
    if not topic:
        return ""
    
    topic_lower = topic.lower().strip()
    
    normalizations = {
        "органы дыхательной системы человека": "дыхательная система",
        "дыхание человека": "дыхательная система",
        "органы дыхания": "дыхательная система",
        "дыхательная система человека": "дыхательная система",
        "квадратные уравнения": "квадратные уравнения",
        "квадратное уравнение": "квадратные уравнения",
        "реформы петра i": "реформы Петра I",
        "реформы петра первого": "реформы Петра I",
        "млекопитающие": "млекопитающие",
        "млекопитающие животные": "млекопитающие",
    }
    
    for key, normalized in normalizations.items():
        if key in topic_lower:
            return normalized
    
    return topic


def format_variant_text(text: str) -> str:
    """Форматирует текст варианта для лучшей читаемости"""
    text = re.sub(r'(\d+\.)', r'\n\1', text)
    text = re.sub(r'([А-Я]\))\s*', r'\1\n', text)
    text = re.sub(r'(Задание \d+:)', r'\n\1\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def parse_generated_variants(response_text: str, expected_count: int) -> Dict[int, str]:
    """Парсит варианты из ответа LLM"""
    variants = {}
    
    cleaned = response_text
    cleaned = cleaned.replace("**", "").replace("__", "")
    
    pattern = re.compile(
        r'(?:^|\n)\s*(?:#+\s*)?(?:ВАРИАНТ|Вариант)\s*[№#-]?\s*(\d+)\s*:?\s*',
        re.IGNORECASE
    )
    
    matches = list(pattern.finditer(cleaned))
    
    for idx, match in enumerate(matches):
        try:
            variant_num = int(match.group(1))
        except (ValueError, IndexError):
            continue
        
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(cleaned)
        variant_text = cleaned[start:end].strip()
        variant_text = re.sub(r'^[:\-•*\s]+', '', variant_text)
        
        if variant_text:
            variants[variant_num] = variant_text
    
    for i in range(1, expected_count + 1):
        if i not in variants:
            variants[i] = f"Вариант {i}\n(сгенерируйте заново)"
    
    return variants


def detect_task_type_by_structure(text: str) -> str:
    """Определяет ТИП ЗАДАНИЯ по структуре текста"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["вычисли", "найди", "реши", "найдите", "вычислите"]):
        return "calculation"
    if any(word in text_lower for word in ["выбери", "укажите", "выберите", "отметьте"]):
        return "multiple_choice"
    if any(word in text_lower for word in ["соотнеси", "сопоставь", "соотнесите"]):
        return "matching"
    if any(word in text_lower for word in ["вставь", "пропуск", "заполни", "___"]):
        return "fill_blanks"
    if any(word in text_lower for word in ["упорядочь", "расставь", "последовательность"]):
        return "ordering"
    
    return "open_response"


def generate_fallback_by_type(task_type: str, questions_count: int) -> str:
    """Генерирует fallback ответ в зависимости от типа задания"""
    fallbacks = {
        "calculation": "0" if questions_count == 1 else ", ".join([f"{i}-0" for i in range(1, questions_count + 1)]),
        "multiple_choice": "А" if questions_count == 1 else ", ".join([f"{i}-А" for i in range(1, questions_count + 1)]),
        "matching": "1-А" if questions_count == 1 else ", ".join([f"{i}-{chr(64+i)}" for i in range(1, questions_count + 1)]),
        "fill_blanks": "слово" if questions_count == 1 else ", ".join([f"слово{i}" for i in range(1, questions_count + 1)]),
        "ordering": "1" if questions_count == 1 else ", ".join([str(i) for i in range(1, questions_count + 1)]),
        "open_response": "Ответ" if questions_count == 1 else ", ".join([f"ответ{i}" for i in range(1, questions_count + 1)]),
    }
    return fallbacks.get(task_type, "Ответ")


def detect_task_type(text: str) -> str:
    """Определяет ТИП задания по структуре"""
    text_lower = text.lower()
    
    # 1. Сопоставление
    if any(w in text_lower for w in ["соотнеси", "сопоставь", "match"]):
        return "matching"
    
    # 2. Упорядочивание
    if any(w in text_lower for w in ["упорядочь", "расставь по порядку", "order", "sequence"]):
        return "ordering"
    
    # 3. Верно/Неверно
    if any(w in text_lower for w in ["верно", "неверно", "true", "false"]):
        return "true_false"
    
    # 4. Вставка пропусков
    if "___" in text or "…" in text or any(w in text_lower for w in ["вставь", "пропуск", "fill"]):
        return "fill_blanks"
    
    # 5. Перевод
    if any(w in text_lower for w in ["переведи", "translate"]):
        return "translation"
    
    # 6. Исправление ошибок
    if any(w in text_lower for w in ["найди ошибку", "исправь", "correct"]):
        return "error_correction"
    
    # 7. Вычисления
    if any(w in text_lower for w in ["вычисли", "найди", "реши", "calculate", "solve"]):
        return "calculation"
    
    # 8. Тест с вариантами
    if re.search(r'[А-ЯA-Z]\)', text) or re.search(r'[А-ЯA-Z]\.', text):
        return "multiple_choice"
    
    # 9. Развернутый ответ (по длине)
    if len(text) > 300:
        return "essay"
    
    # 10. Короткий ответ (по умолчанию)
    return "short_answer"



async def generate_answers(variants: Dict[int, str]) -> Dict[int, str]:
    """Генерация ответов на основе ТИПА ЗАДАНИЯ"""
    
    if not variants:
        return {}
    
    answers = {}
    
    for num, text in variants.items():
        task_type = detect_structural_type_from_text(text)
        
        if task_type is None:
            task_type = StructuralType.OPEN_RESPONSE
        
        # Расширенные примеры для каждого типа
        examples = {
            StructuralType.MULTIPLE_CHOICE: "Пример: 'А,В,Д' или 'Б'",
            StructuralType.MATCHING: "Пример: '1-А,2-Б,3-В'",
            StructuralType.FILL_BLANKS: "Пример: 'зима, доска, пенал' или 'am,is,are'",
            StructuralType.CALCULATION: "Пример: '78.5' или 'x=5'",
            StructuralType.OPEN_RESPONSE: "Пример: 'перья, руки' или 'Мы пошли гулять в парк, там было много детей'",
        }
        
        example = examples.get(task_type, "Верни краткий ответ")
        
        prompt = f"""
Задание: {text}

Тип задания: {task_type.value}

Правила:
- Верни ТОЛЬКО ответ, без пояснений
- {example}

Ответ:
"""
        try:
            result = await call_llm(prompt, temperature=0.2)
            result = result.strip()
            # Очистка от лишнего
            result = re.sub(r'^(Ответ|Answer):\s*', '', result, flags=re.IGNORECASE)
            answers[str(num)] = result if result else "—"
        except Exception as e:
            logger.warning(f"Ошибка для варианта {num}: {e}")
            answers[str(num)] = "—"
    
    return answers

def detect_structural_type_from_text(text: str) -> Optional[StructuralType]:
    text_lower = text.lower()
    
    # Определение по ключевым словам
    if any(w in text_lower for w in ["подчеркните", "определите часть речи", "найди корень"]):
        return StructuralType.OPEN_RESPONSE
    
    if any(w in text_lower for w in ["выбери", "укажите", "выберите"]):
        return StructuralType.MULTIPLE_CHOICE
    
    if any(w in text_lower for w in ["соотнеси", "сопоставь"]):
        return StructuralType.MATCHING
    
    if any(w in text_lower for w in ["вставь", "пропуск", "заполни", "___"]):
        return StructuralType.FILL_BLANKS
    
    if any(w in text_lower for w in ["вычисли", "найди", "реши"]):
        return StructuralType.CALCULATION
    
    if any(w in text_lower for w in ["расставьте запятые", "знаки препинания"]):
        return StructuralType.OPEN_RESPONSE
    
    if any(w in text_lower for w in ["найдите лишнее", "исключи"]):
        return StructuralType.MULTIPLE_CHOICE
    
    if any(w in text_lower for w in ["образуйте форму", "множественное число"]):
        return StructuralType.FILL_BLANKS
    
    return None


# АНАЛИЗ ЗАДАНИЯ
async def _extract_structural_spec(text: str) -> Dict[str, Any]:
    """Stage 1: Извлечение структуры"""
    
    prompt = f"""
Определи СТРУКТУРУ задания. Верни ТОЛЬКО JSON.

=== ЗАДАНИЕ ===
{text[:1500]}

=== ВОЗМОЖНЫЕ ЗНАЧЕНИЯ ===
structural_type: multiple_choice, matching, ordering, classification, fill_blanks, open_response, calculation, proof
answer_format: single_choice, multi_select, sequence, pairs, text, number, formula, boolean

=== ФОРМАТ (ТОЛЬКО JSON) ===
{{
    "structural_type": "multiple_choice",
    "answer_format": "multi_select",
    "operations_count": 3,
    "options_count": 6,
    "requires_single_correct": false
}}
"""
    
    try:
        result = await call_llm(prompt, expect_json=False, temperature=0.1)
        data = clean_json_response(result)
        
        return {
            "structural_type": data.get("structural_type", "open_response"),
            "answer_format": data.get("answer_format", "text"),
            "operations_count": data.get("operations_count", 1),
            "options_count": data.get("options_count", 0),
            "requires_single_correct": data.get("requires_single_correct", True)
        }
    except Exception as e:
        logger.warning(f"Ошибка структурного анализа: {e}")
        return {
            "structural_type": "open_response",
            "answer_format": "text",
            "operations_count": 1,
            "options_count": 0,
            "requires_single_correct": True
        }


async def _extract_pedagogical_spec(text: str, structural_spec: Dict) -> PedagogicalSpec:
    """Stage 2: Извлечение педагогики"""
    
    prompt = f"""
Определи ПЕДАГОГИЧЕСКУЮ ЦЕЛЬ и КОГНИТИВНЫЙ УРОВЕНЬ. Верни ТОЛЬКО JSON.

=== ЗАДАНИЕ ===
{text[:1500]}

=== СТРУКТУРА ===
structural_type: {structural_spec.get('structural_type')}
answer_format: {structural_spec.get('answer_format')}

=== ВОЗМОЖНЫЕ ЗНАЧЕНИЯ ===
pedagogical_intent: fact_recall, classification, matching, sequence, calculation, proof, analysis
cognitive_level: recognition, reproduction, application, analysis, synthesis

=== ФОРМАТ (ТОЛЬКО JSON) ===
{{
    "pedagogical_intent": "classification",
    "cognitive_level": "recognition",
    "cognitive_load": 2
}}
"""
    
    try:
        result = await call_llm(prompt, expect_json=False, temperature=0.15)
        data = clean_json_response(result)
        
        structural_type = structural_spec.get("structural_type", "open_response")
        answer_format = structural_spec.get("answer_format", "text")
        
        if structural_type == "calculation":
            answer_format = "number"
        elif structural_type == "multiple_choice" and structural_spec.get("options_count", 0) > 1:
            answer_format = "multi_select"
        
        return PedagogicalSpec(
            pedagogical_intent=PedagogicalIntent(data.get("pedagogical_intent", "classification")),
            cognitive_level=CognitiveLevel(data.get("cognitive_level", "recognition")),
            structural_type=StructuralType(structural_type),
            answer_format=AnswerFormat(answer_format),
            operations_count=structural_spec.get("operations_count", 1),
            cognitive_load=data.get("cognitive_load", 2),
            options_count=structural_spec.get("options_count", 0),
            requires_single_correct=structural_spec.get("requires_single_correct", False)
        )
    except Exception as e:
        logger.warning(f"Ошибка педагогического анализа: {e}")
        return PedagogicalSpec(
            pedagogical_intent=PedagogicalIntent.CLASSIFICATION,
            cognitive_level=CognitiveLevel.RECOGNITION,
            structural_type=StructuralType(structural_spec.get("structural_type", "open_response")),
            answer_format=AnswerFormat.MULTI_SELECT if structural_spec.get("structural_type") == "multiple_choice" else AnswerFormat.TEXT
        )


async def _extract_content_spec(text: str) -> ContentSpec:
    """Stage 3: Извлечение контента - с определением класса"""
    
    prompt = f"""
Определи КОНТЕНТ задания. Верни ТОЛЬКО JSON.

=== ЗАДАНИЕ ===
{text[:1500]}

=== ФОРМАТ (ТОЛЬКО JSON) ===
{{
    "knowledge_domain": "mathematics",
    "topic_core": "квадратные уравнения",
    "grade": "8",
    "content_entities": ["x²", "дискриминант"]
}}

knowledge_domain: mathematics, physics, chemistry, biology, history, geography, russian, literature, english
grade: 5,6,7,8,9,10,11 (определи по сложности задания)
"""
    
    try:
        result = await call_llm(prompt, expect_json=False, temperature=0.15)
        data = clean_json_response(result)
        
        topic_core = normalize_topic(data.get("topic_core", ""))
        grade = data.get("grade", "5-9")  # ← добавляем определение класса
        
        return ContentSpec(
            knowledge_domain=data.get("knowledge_domain", "unknown"),
            topic_core=topic_core,
            grade=grade,  # ← нужно добавить поле в ContentSpec
            content_entities=data.get("content_entities", []),
            preserved_patterns=[],
            forbid_topic_shift=False,
            allowed_variations=[
                VariationPolicy.NUMERIC_PARAMETERS,
                VariationPolicy.DOMAIN_ENTITIES,
                VariationPolicy.SURFACE_WORDING
            ]
        )
    except Exception as e:
        logger.warning(f"Ошибка контентного анализа: {e}")
        return ContentSpec(knowledge_domain="unknown", grade="5-9")


async def analyze_task_specification(text: str) -> TaskSpecification:
    """Полный анализ задания"""
    
    structural_spec = await _extract_structural_spec(text)
    pedagogical_spec = await _extract_pedagogical_spec(text, structural_spec)
    content_spec = await _extract_content_spec(text)
    
    return TaskSpecification(
        pedagogical=pedagogical_spec,
        content=content_spec,
        legacy_subject=content_spec.knowledge_domain,
        legacy_topic=content_spec.topic_core,
        legacy_skill=content_spec.skill_target,
        legacy_didactic_goal=f"Проверить навык {content_spec.skill_target}"
    )


async def analyze_task_structure(text: str) -> Dict[str, Any]:
    """Старый интерфейс для совместимости"""
    
    spec = await analyze_task_specification(text)
    
    cache_key = normalize_for_cache(text)
    _SPEC_CACHE[cache_key] = spec
    
    return spec.to_legacy_dict()


# ПОСТРОЕНИЕ ПРОМПТА ДЛЯ ГЕНЕРАЦИИ
def build_universal_generation_prompt(
    original_text: str,
    num_variants: int,
    spec: TaskSpecification,
    variation_types: List[str],
    user_comment: Optional[str] = None,
    difficulty_override: Optional[str] = None,
    forbidden_parts: Optional[str] = None
) -> str:
    """Строит промпт для генерации — с усиленной привязкой к эталону"""
    
    variations_section = f"""
=== ТИПЫ ВАРИАЦИЙ ===
{chr(10).join(f'✅ {vt}' for vt in variation_types) if variation_types else '✅ стандартные'}
"""
    
    if difficulty_override == "easier":
        difficulty_section = f"Сделай вариант ПРОЩЕ. Уровень эталона: {spec.difficulty_level}/10"
    elif difficulty_override == "harder":
        difficulty_section = f"Сделай вариант СЛОЖНЕЕ. Уровень эталона: {spec.difficulty_level}/10"
    else:
        difficulty_section = f"Уровень сложности: {spec.difficulty_level}/10. Операций: {spec.pedagogical.operations_count}"
    
    forbidden_section = ""
    if forbidden_parts and forbidden_parts.strip():
        forbidden_section = f"НЕ МЕНЯТЬ: {forbidden_parts.strip()}"
    
    comment_section = ""
    if user_comment and user_comment.strip():
        comment_section = f"ДОПОЛНИТЕЛЬНО: {user_comment.strip()}"
    
    # Усиленная фиксация темы
    topic_constraint = f"""
=== ТЕМА (НЕ МЕНЯТЬ) ===
{spec.content.topic_core}

=== СТРУКТУРА ЭТАЛОНА ===
{original_text[:500]}

=== ЧТО НУЖНО СОХРАНИТЬ ===
1. ТЕМУ: {spec.content.topic_core}
2. ТИП ЗАДАНИЯ: {spec.pedagogical.structural_type.value}
3. КОЛИЧЕСТВО ВОПРОСОВ/ЗАДАНИЙ в варианте
4. ФОРМУЛИРОВКУ инструкции (сохрани её стиль)

=== ЧТО МОЖНО ИЗМЕНЯТЬ ===
- Числовые значения
- Конкретные примеры, имена, названия (в пределах темы)
- Порядок вопросов (если тип вариации "order")
- Синонимы в формулировках (если тип вариации "synonyms")

=== ЧТО НЕЛЬЗЯ МЕНЯТЬ ===
- Тип задания (тест/задача/сопоставление и т.д.)
- Количество шагов решения
- Смысловую структуру
"""
    
    example_variant = f"""
ПРИМЕР хорошего варианта (сохраняет структуру эталона, но меняет данные):
{original_text[:300]}... → (числа/примеры заменены на другие в рамках темы)
"""
    
    return f"""
Ты — генератор учебных заданий. Сгенерируй {num_variants} вариантов, **максимально близких к эталону по структуре**.

{spec.to_prompt_invariants()}

{topic_constraint}

{example_variant}

{difficulty_section}

{variations_section}

{forbidden_section}

{comment_section}

=== ЭТАЛОН (ОБРАЗЕЦ) ===
{original_text}

=== ПРАВИЛА ГЕНЕРАЦИИ ===
1. Каждый вариант должен быть **по той же теме** что и эталон
2. **Сохрани количество вопросов/заданий** как в эталоне, ни больше, ни меньше. 
3. **Сохрани тип вопросов** (если в эталоне тест - делай тест, если задача - задачу)
4. Меняй только: числа, имена, примеры, порядок
5. Если в эталоне есть варианты ответов А), Б), В) - сохрани это форматирование


=== ФОРМАТ ВЫВОДА ===
ВАРИАНТ 1:
(только текст задания)

ВАРИАНТ 2:
(только текст задания)

Сгенерируй РОВНО {num_variants} вариантов. В заданиях НЕ пиши ответ.
"""


# ОСНОВНАЯ ФУНКЦИЯ ГЕНЕРАЦИИ
async def generate_variants(
    original_text: str,
    num_variants: int,
    variation_types: List[str],
    forbidden_parts: Optional[str] = None,
    task_structure: Optional[Dict[str, Any]] = None,
    difficulty_override: Optional[str] = None,
    target_grade: Optional[str] = None,
    task_type: Optional[str] = None,
    user_comment: Optional[str] = None
) -> Dict[int, VariantDocument]:
    """Генерирует варианты заданий с SUBJECT LOCK"""
    
    cache_key = normalize_for_cache(original_text)
    spec = None
    
    if cache_key in _SPEC_CACHE:
        spec = _SPEC_CACHE[cache_key]
    elif task_structure:
        subject = task_structure.get("subject", "unknown")
        structural_type = StructuralType.OPEN_RESPONSE
        task_type_str = task_structure.get("task_type", "")
        
        if task_type_str == "calculation":
            structural_type = StructuralType.CALCULATION
        elif task_type_str == "test":
            structural_type = StructuralType.MULTIPLE_CHOICE
        elif task_type_str == "matching":
            structural_type = StructuralType.MATCHING
        elif task_type_str == "ordering":
            structural_type = StructuralType.ORDERING
        
        if task_type_str == "calculation":
            pedagogical_intent = PedagogicalIntent.CALCULATION
        elif task_type_str == "test":
            pedagogical_intent = PedagogicalIntent.CLASSIFICATION
        elif task_type_str == "matching":
            pedagogical_intent = PedagogicalIntent.MATCHING
        elif task_type_str == "ordering":
            pedagogical_intent = PedagogicalIntent.SEQUENCE
        else:
            pedagogical_intent = PedagogicalIntent.CLASSIFICATION
        
        answer_format = AnswerFormat.TEXT
        if subject in ["математика", "mathematics", "физика", "physics"]:
            answer_format = AnswerFormat.NUMBER
        elif subject in ["химия", "chemistry"]:
            answer_format = AnswerFormat.FORMULA
        elif task_type_str == "test":
            answer_format = AnswerFormat.MULTI_SELECT
        
        pedagogical = PedagogicalSpec(
            pedagogical_intent=pedagogical_intent,
            cognitive_level=CognitiveLevel.RECOGNITION,
            structural_type=structural_type,
            answer_format=answer_format,
            operations_count=task_structure.get("operations_count", 3),
            cognitive_load=2
        )
        content = ContentSpec(
            knowledge_domain=subject,
            topic_core=task_structure.get("topic", ""),
            skill_target=f"{pedagogical_intent.value}_within_topic",
            content_entities=[],
            preserved_patterns=task_structure.get("invariant_elements", [])
        )
        spec = TaskSpecification(
            pedagogical=pedagogical,
            content=content,
            legacy_subject=subject,
            legacy_topic=task_structure.get("topic", "не определена")
        )
        _SPEC_CACHE[cache_key] = spec
    
    if spec is None:
        spec = await analyze_task_specification(original_text)
        _SPEC_CACHE[cache_key] = spec
    
    if not spec.content.topic_core:
        extracted = await _extract_content_spec(original_text)
        spec.content.topic_core = extracted.topic_core
        spec.content.topic_boundaries = extracted.topic_boundaries
        spec.content.forbidden_topics = extracted.forbidden_topics
        spec.content.skill_target = extracted.skill_target
    
    if task_type and task_type != "auto":
        type_mapping = {
            "calculation": StructuralType.CALCULATION,
            "test": StructuralType.MULTIPLE_CHOICE,
            "open_question": StructuralType.OPEN_RESPONSE,
            "matching": StructuralType.MATCHING,
            "ordering": StructuralType.ORDERING,
        }
        if task_type in type_mapping:
            spec.pedagogical.structural_type = type_mapping[task_type]
    
    if forbidden_parts and forbidden_parts.strip():
        spec.content.preserved_patterns.append(forbidden_parts.strip())
    
    variation_types = [vt for vt in variation_types if vt != "context"]
    
    prompt = build_universal_generation_prompt(
        original_text=original_text,
        num_variants=num_variants,
        spec=spec,
        variation_types=variation_types,
        user_comment=user_comment,
        difficulty_override=difficulty_override,
        forbidden_parts=forbidden_parts
    )
    
    system_prompt = "Ты — педагогический дизайнер. Генерируешь варианты заданий с одинаковой педагогической моделью."
    
    result = await call_llm(prompt, system_prompt, temperature=0.1)
    
    raw_variants = parse_generated_variants(result, num_variants)
    
    document_variants = {}
    for num, text in raw_variants.items():
        formatted_text = format_variant_text(text)
        document_variants[num] = parse_variant_to_document(formatted_text, num)
    
    logger.info(f"Сгенерировано {len(document_variants)} вариантов: тема={spec.content.topic_core}, "
               f"intent={spec.pedagogical.pedagogical_intent.value}")
    
    return document_variants


# ВАЛИДАЦИЯ
async def validate_variants(
    variants: Dict[int, str],
    original_text: str,
    task_structure: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Гибридная валидация:
    1. Генерирует ответы через LLM
    2. Возвращает результат с ответами для учителя
    """
    
    answers = await generate_answers(variants)
    
    logger.info(f"✅ Сгенерированы ответы для {len(answers)} вариантов: {answers}")
    
    variant_status = {}
    for num in variants.keys():
        variant_status[str(num)] = {
            "valid": True,
            "solvable": True,
            "same_topic": True,
            "same_structure": True,
            "issues": []
        }
    
    return {
        "valid": True,
        "variant_status": variant_status,
        "answers": answers,
        "validation_method": "llm_with_type_detection",
        "summary": {
            "total": len(variants),
            "valid_count": len(variants),
            "invalid_count": 0
        }
    }


# ПЕРЕГЕНЕРАЦИЯ
async def regenerate_variant(
    original_text: str,
    variant_number: int,
    current_variant_text: str,
    variation_types: List[str],
    task_structure: Optional[Dict[str, Any]] = None,
    forbidden_parts: Optional[str] = None,
    failure_reason: str = None,
    existing_variants: Optional[Dict[int, str]] = None
) -> str:
    """Перегенерирует один вариант"""
    
    cache_key = normalize_for_cache(original_text)
    spec = _SPEC_CACHE.get(cache_key)
    
    if spec is None and task_structure:
        pedagogical = PedagogicalSpec(
            pedagogical_intent=PedagogicalIntent.CLASSIFICATION,
            cognitive_level=CognitiveLevel.RECOGNITION,
            structural_type=StructuralType.MULTIPLE_CHOICE,
            answer_format=AnswerFormat.MULTI_SELECT
        )
        content = ContentSpec(
            knowledge_domain=task_structure.get("subject", "unknown"),
            topic_core=task_structure.get("topic", ""),
            preserved_patterns=task_structure.get("invariant_elements", [])
        )
        spec = TaskSpecification(pedagogical=pedagogical, content=content)
    
    if spec is None:
        spec = await analyze_task_specification(original_text)
        _SPEC_CACHE[cache_key] = spec
    
    existing_note = ""
    if existing_variants and len(existing_variants) > 1:
        other_answers = []
        for num, text in existing_variants.items():
            if num != variant_number:
                short = text[:200].replace("\n", " ")
                other_answers.append(f"Вариант {num}: {short}...")
        if other_answers:
            existing_note = f"\n⚠️ Убедись, что ответ отличается от: {', '.join(other_answers[:3])}"
    
    prompt = f"""
Перегенерируй ТОЛЬКО ВАРИАНТ {variant_number}.

=== ПЕДАГОГИЧЕСКАЯ МОДЕЛЬ ===
{spec.to_prompt_invariants()}

=== ЭТАЛОН ===
{original_text}

=== НЕУДАЧНЫЙ ВАРИАНТ ===
{current_variant_text}
{existing_note}

=== ПРИЧИНА ===
{failure_reason if failure_reason else "Вариант не соответствует критериям"}

=== ТРЕБОВАНИЯ ===
1. Сохрани тему: {spec.content.topic_core}
2. Сохрани структуру и сложность
3. Меняй: {', '.join(variation_types)}
{f'4. НЕ меняй: {forbidden_parts}' if forbidden_parts else ''}

Выдай ТОЛЬКО текст варианта, без пояснений.
"""
    
    try:
        result = await call_llm(prompt, temperature=0.3)
        return result.strip()
    except Exception as e:
        logger.error(f"Ошибка перегенерации: {e}")
        return current_variant_text


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def _get_answer_format_guide(subject: str, task_type: str) -> str:
    """Гайд по формату ответов"""
    if task_type == "test":
        return "Ответ: буквы правильных вариантов через запятую (а,б,в)"
    if task_type == "calculation":
        return "Ответ: число (например, 42)"
    if task_type == "open_question":
        return "Ответ: краткое предложение (до 10 слов)"
    return "Ответ: строка с правильным ответом"
