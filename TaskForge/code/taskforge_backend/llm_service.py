import httpx
import os
import json
import logging
import re
import base64
import uuid
import time
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Конфигурация GigaChat (через Authorization Key)
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

# Кэш токена
_cached_token: Optional[str] = None
_token_expires_at: float = 0

# Пресеты вариаций из кейса
VARIATION_PRESETS = {
    "minimal": ["numbers"],
    "standard": ["numbers", "order"],
    "full": ["numbers", "order", "synonyms", "context"]
}


# HELPER: Авторизация в GigaChat (через credentials)
async def _get_access_token() -> str:
    global _cached_token, _token_expires_at
    
    if _cached_token and time.time() < _token_expires_at - 300:
        return _cached_token
    
    if not GIGACHAT_CREDENTIALS:
        raise ValueError("Нет credentials")
    
    headers = {
        "Authorization": f"Bearer {GIGACHAT_CREDENTIALS}",
        "Content-Type": "application/x-www-form-urlencoded",
        "RqUID": str(uuid.uuid4()),
    }
    
    body = {"scope": GIGACHAT_SCOPE}
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        response = await client.post(GIGACHAT_AUTH_URL, headers=headers, data=body)
        response.raise_for_status()
        data = response.json()
        
        _cached_token = data.get("access_token")
        # Если нет expires_in, ставим 30 минут по умолчанию
        _token_expires_at = time.time() + data.get("expires_in", 1800)
        
        logger.info(f"Получен новый Access Token")
        return _cached_token


# HELPER: Очистка JSON от LLM
def clean_json_response(result: str) -> dict:
    """Очищает ответ LLM от markdown и мусора, парсит JSON"""
    result = result.strip()
    
    # Удаляем markdown-обёртки
    if result.startswith("```json"):
        result = result[7:]
    elif result.startswith("```"):
        result = result[3:]
    
    if result.endswith("```"):
        result = result[:-3]
    
    # Ищем первый { и последний }
    first_brace = result.find('{')
    last_brace = result.rfind('}')
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        result = result[first_brace:last_brace + 1]
    
    return json.loads(result)


# HELPER: Парсинг сгенерированных вариантов
def parse_generated_variants(response_text: str, expected_count: int) -> Dict[int, str]:
    """Парсит ответ LLM в словарь {номер_варианта: текст}"""
    variants = {}
    lines = response_text.split('\n')
    current_variant = None
    current_text = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        line_lower = line_stripped.lower()
        
        is_variant_start = False
        variant_num = None
        
        # Вариант 1: "ВАРИАНТ 1: текст"
        if 'вариант' in line_lower or 'variant' in line_lower:
            match = re.search(r'(\d+)', line_stripped)
            if match:
                variant_num = int(match.group(1))
                is_variant_start = True
                parts = line_stripped.split(':', 1)
                if len(parts) > 1:
                    current_text = [parts[1].strip()]
                else:
                    current_text = []
        
        # Вариант 2: "1. текст" или "1) текст"
        if not is_variant_start:
            match = re.match(r'^(\d+)[\.\)]\s+(.+)', line_stripped)
            if match:
                variant_num = int(match.group(1))
                is_variant_start = True
                current_text = [match.group(2).strip()]
        
        if is_variant_start:
            if current_variant is not None:
                variants[current_variant] = '\n'.join(current_text).strip()
            current_variant = variant_num
        else:
            if current_variant is not None:
                current_text.append(line_stripped)
    
    # Сохраняем последний вариант
    if current_variant is not None:
        variants[current_variant] = '\n'.join(current_text).strip()
    
    # Fallback
    if not variants:
        logger.warning("Не удалось распарсить варианты, использую fallback")
        for i in range(1, expected_count + 1):
            variants[i] = f"Вариант {i}\n{response_text[:200]}"
    
    return variants



# Базовый вызов LLM (с поддержкой реального API + мок)

async def call_llm(
    prompt: str, 
    system_prompt: str = None,
    expect_json: bool = False
) -> str:
    """ Базовый вызов GigaChat с авторизацией через credentials.
    Если credentials нет — использует мок-режим.
    """
    # Проверяем, есть ли credentials
    use_mock = False
    if not GIGACHAT_CREDENTIALS or GIGACHAT_CREDENTIALS == "ваш_credentials_здесь":
        use_mock = True
        logger.info("Нет GIGACHAT_CREDENTIALS, использую мок-режим")
        return _mock_llm_response(prompt)
    
    try:
        access_token = await _get_access_token()
    except Exception as e:
        logger.warning(f"Не удалось получить токен: {e}. Использую мок-режим")
        return _mock_llm_response(prompt)
    
    # Собираем сообщения
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    final_prompt = prompt
    if expect_json:
        final_prompt = f"{prompt}\n\nВерни ТОЛЬКО JSON, без пояснений и markdown-обёрток."
    
    messages.append({"role": "user", "content": final_prompt})
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "GigaChat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    # Retry logic
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                response = await client.post(GIGACHAT_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                if "choices" not in data or not data["choices"]:
                    raise ValueError("Некорректный ответ LLM: нет choices")
                
                return data["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            logger.warning(f"Таймаут LLM, попытка {attempt + 1}/{max_retries + 1}")
            if attempt == max_retries:
                if use_mock:
                    return _mock_llm_response(prompt)
                raise Exception("Превышено время ожидания LLM")
        except Exception as e:
            logger.warning(f"Ошибка LLM, попытка {attempt + 1}/{max_retries + 1}: {e}")
            if attempt == max_retries:
                if use_mock:
                    return _mock_llm_response(prompt)
                raise


def _mock_llm_response(prompt: str) -> str:
    """Мок-ответ для демонстрации (для тестирования без ключей)."""
    prompt_lower = prompt.lower()
    
    if "анализ" in prompt_lower or "структур" in prompt_lower:
        return json.dumps({
            "subject": "математика",
            "task_type": "линейное уравнение",
            "difficulty_score": 6,
            "operations_count": 3,
            "grade": "7-8",
            "variable_elements": ["числа", "коэффициенты"],
            "invariant_elements": ["структура уравнения", "количество шагов"],
            "recommended_variations": ["numbers", "order"],
            "why_difficulty": "3 шага решения, линейное уравнение",
            "why_invariant": "структура ax + b = c сохраняется",
            "why_variable": "числа можно менять без потери смысла"
        })
    elif "валидация" in prompt_lower or "проверь" in prompt_lower:
        return json.dumps({
            "valid": True,
            "difficulty_match": True,
            "unique_answers": True,
            "same_structure": True,
            "all_solvable": True,
            "issues": [],
            "explanations": {
                "difficulty_match": "Все варианты имеют 3 шага решения",
                "same_structure": "Структура ax + b = c сохранена",
                "all_solvable": "Каждое уравнение имеет решение"
            },
            "answers": {
                "1": "x = 5",
                "2": "x = 4",
                "3": "x = 6",
                "4": "x = 5"
            }
        })
    else:
        return """
ВАРИАНТ 1: Решите уравнение: 3x + 7 = 22
ВАРИАНТ 2: Решите уравнение: 5x - 3 = 17
ВАРИАНТ 3: Решите уравнение: 2x + 9 = 21
ВАРИАНТ 4: Решите уравнение: 4x - 5 = 15
"""


# Анализ структуры задания
async def analyze_task_structure(text: str) -> Dict[str, Any]:
    """Анализирует структуру задания"""
    prompt = f"""
Проанализируй это задание и верни ТОЛЬКО JSON:

Задание:
{text[:1000]}

Формат:
{{
    "subject": "предмет",
    "task_type": "тип задания",
    "difficulty_score": число от 1 до 10,
    "operations_count": число шагов,
    "grade": "класс",
    "variable_elements": ["элемент1", "элемент2"],
    "invariant_elements": ["элемент1", "элемент2"],
    "recommended_variations": ["numbers", "order", "synonyms", "context"],
    "why_difficulty": "почему такая сложность",
    "why_invariant": "почему эти элементы нельзя менять",
    "why_variable": "почему эти элементы можно менять"
}}
"""

    system_prompt = "Ты — эксперт по методике. Анализируешь структуру учебных заданий."

    try:
        result = await call_llm(prompt, system_prompt, expect_json=True)
        data = clean_json_response(result)
        logger.info(f"Анализ задания: {data.get('task_type')}, сложность {data.get('difficulty_score')}")
        return data
    except Exception as e:
        logger.warning(f"Ошибка анализа: {e}. Возвращаю default.")
        return {
            "subject": "не определён",
            "task_type": "не определён",
            "difficulty_score": 5,
            "operations_count": 3,
            "grade": "5-9",
            "variable_elements": ["числа", "параметры"],
            "invariant_elements": ["структура", "алгоритм решения"],
            "recommended_variations": ["numbers", "order"],
            "why_difficulty": "Стандартный уровень сложности",
            "why_invariant": "Методически важно сохранить структуру",
            "why_variable": "Числовые значения могут варьироваться"
        }


# Построение промпта для генерации
def build_generation_prompt(
    original_text: str,
    num_variants: int,
    variation_types: List[str],
    forbidden_parts: Optional[str] = None,
    task_structure: Optional[Dict[str, Any]] = None,
    difficulty_override: Optional[str] = None,  # "easier", "same", "harder"
    target_grade: Optional[str] = None
) -> str:
    """Строит промпт для генерации вариантов на основе анализа структуры и выбора пользователя."""
    
    variant_types_str = ", ".join(variation_types)
    forbid_str = f"\nЗапрещено изменять: {forbidden_parts}" if forbidden_parts else ""
    
    invariant_str = ""
    variable_str = ""
    difficulty_str = ""
    
    if task_structure:
        invariant_elements = task_structure.get("invariant_elements", [])
        variable_elements = task_structure.get("variable_elements", [])
        
        if invariant_elements:
            invariant_str = f"""
ИНВАРИАНТНЫЕ ЭЛЕМЕНТЫ (НЕЛЬЗЯ МЕНЯТЬ):
{chr(10).join(f'- {elem}' for elem in invariant_elements)}
"""
        
        if variable_elements:
            variable_str = f"""
ВАРИАТИВНЫЕ ЭЛЕМЕНТЫ (МОЖНО МЕНЯТЬ):
{chr(10).join(f'- {elem}' for elem in variable_elements)}
"""
    
    #  ЛОГИКА ВЫБОРА СЛОЖНОСТИ
    if difficulty_override == "easier":
        difficulty_str = """
ТРЕБОВАНИЯ К СЛОЖНОСТИ:
- Сделай вариант ПРОЩЕ, чем эталон
- Уменьши количество операций или упрости вычисления
- Сохрани тип задания и дидактическую цель
- Задания должны оставаться решаемыми для более слабых учеников
"""
    elif difficulty_override == "harder":
        difficulty_str = """
ТРЕБОВАНИЯ К СЛОЖНОСТИ:
- Сделай вариант СЛОЖНЕЕ, чем эталон
- Добавь дополнительные шаги или усложни вычисления
- Сохрани тип задания и дидактическую цель
- Задания должны оставаться корректными для сильных учеников
"""
    else:  # "same" или None
        if task_structure:
            difficulty_str = f"""
ТРЕБОВАНИЯ К СЛОЖНОСТИ:
- Уровень сложности: {task_structure.get('difficulty_score', 5)}/10
- Количество операций: {task_structure.get('operations_count', 3)}
- Целевой класс: {target_grade or task_structure.get('grade', '5-9')}
- Сохрани сложность ТОЧНО такой же, как в эталоне
"""
        else:
            difficulty_str = """
ТРЕБОВАНИЯ К СЛОЖНОСТИ:
- Сохрани сложность такой же, как в эталоне
- Не добавляй и не убирай шаги решения
"""
    
    # Добавляем информацию о целевом классе, если он указан отдельно
    grade_info = ""
    if target_grade and difficulty_override != "same":
        grade_info = f"\n- Целевой класс: {target_grade}"
        difficulty_str = difficulty_str.rstrip("}") + grade_info + "\n"
    
    return f"""
Ты — методист. Сгенерируй варианты заданий.

=== ЭТАЛОН ===
{original_text}

=== ПАРАМЕТРЫ ===
Вариантов: {num_variants}
Типы вариаций: {variant_types_str}
{forbid_str}
{invariant_str}
{variable_str}
{difficulty_str}

=== ПРАВИЛА ===
1. ✅ Сохрани дидактическую цель задания
2. ✅ Меняй ТОЛЬКО вариативные элементы (числа, порядок, контекст)
3. ❌ НЕ меняй инвариантные элементы
4. ❌ НЕ используй очевидные прогрессии
5. ❌ НЕ создавай нерешаемые задачи
6. ✅ Ответы в разных вариантах не должны совпадать
7. ✅ Все варианты должны иметь ОДИНАКОВЫЙ уровень сложности между собой
8. ❌ **ЗАПРЕЩЕНО генерировать одинаковые или похожие варианты. Каждый вариант должен быть УНИКАЛЬНЫМ по формулировке и числовым данным.**
9. ✅ **Сгенерируй {num_variants} РАЗНЫХ вариантов. Никакие два варианта не должны повторяться.**

Формат: "ВАРИАНТ N: текст задания"

ТЫ ДОЛЖЕН СГЕНЕРИРОВАТЬ РОВНО {num_variants} ВАРИАНТОВ. НЕ БОЛЬШЕ И НЕ МЕНЬШЕ:
"""


# Генерация вариантов (оркестрация)
async def generate_variants(
    original_text: str,
    num_variants: int,
    variation_types: List[str],
    forbidden_parts: Optional[str] = None,
    task_structure: Optional[Dict[str, Any]] = None,
    difficulty_override: Optional[str] = None,
    target_grade: Optional[str] = None
) -> Dict[int, str]:
    prompt = build_generation_prompt(
        original_text=original_text,
        num_variants=num_variants,
        variation_types=variation_types,
        forbidden_parts=forbidden_parts,
        task_structure=task_structure,
        difficulty_override=difficulty_override,
        target_grade=target_grade
    )
    
    system_prompt = "Ты — методист. Генерируешь варианты заданий одинаковой сложности."
    
    result = await call_llm(prompt, system_prompt)
    
    variants = parse_generated_variants(result, num_variants)
    
    logger.info(f"Сгенерировано {len(variants)} вариантов из {num_variants} ожидаемых")
    
    return variants


# Валидация (с ответами для учителя)
async def validate_variants(
    variants: Dict[int, str],
    original_text: str,
    task_structure: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Проверяет варианты и генерирует ответы для учителя."""
    variants_text = "\n\n".join([f"ВАРИАНТ {k}: {v}" for k, v in variants.items()])
    
    invariant_requirements = ""
    if task_structure:
        invariant_elements = task_structure.get("invariant_elements", [])
        if invariant_elements:
            invariant_requirements = f"""
Инвариантные элементы (ДОЛЖНЫ сохраниться):
{chr(10).join(f'- {elem}' for elem in invariant_elements)}
"""
    
    prompt = f"""
Проверь сгенерированные варианты и добавь ответы для учителя.

=== ЭТАЛОН ===
{original_text[:500]}

{invariant_requirements}

=== ВАРИАНТЫ ===
{variants_text}

Верни ТОЛЬКО JSON:
{{
    "valid": true/false,
    "difficulty_match": true/false,
    "unique_answers": true/false,
    "same_structure": true/false,
    "all_solvable": true/false,
    "issues": ["проблема1"],
    "explanations": {{
        "difficulty_match": "объяснение",
        "same_structure": "объяснение"
    }},
    "answers": {{
        "1": "ответ для варианта 1",
        "2": "ответ для варианта 2"
    }},
    "fixed_variants": {{}}
}}
"""

    try:
        result = await call_llm(prompt, expect_json=True)
        data = clean_json_response(result)
        logger.info(f"Валидация: valid={data.get('valid')}")
        return data
    except Exception as e:
        logger.warning(f"Ошибка валидации: {e}. Возвращаю pessimistic результат.")
        return {
            "valid": False,
            "difficulty_match": False,
            "unique_answers": False,
            "same_structure": False,
            "all_solvable": False,
            "issues": ["Ошибка автоматической проверки"],
            "explanations": {},
            "answers": {},
            "fixed_variants": {}
        }


# Перегенерация одного варианта
async def regenerate_variant(
    original_text: str,
    variant_number: int,
    current_variant_text: str,
    variation_types: List[str],
    task_structure: Optional[Dict[str, Any]] = None,
    forbidden_parts: Optional[str] = None
) -> str:
    """Перегенерирует один вариант с сохранением структуры."""
    
    variant_types_str = ", ".join(variation_types)
    forbid_str = f"\nЗапрещено изменять: {forbidden_parts}" if forbidden_parts else ""
    
    invariant_str = ""
    if task_structure:
        invariant_elements = task_structure.get("invariant_elements", [])
        if invariant_elements:
            invariant_str = f"""
НЕЛЬЗЯ МЕНЯТЬ:
{chr(10).join(f'- {elem}' for elem in invariant_elements)}
"""
    
    prompt = f"""
Перегенерируй ТОЛЬКО ВАРИАНТ {variant_number}.

=== ЭТАЛОН ===
{original_text}

=== ПЛОХОЙ ВАРИАНТ ===
{current_variant_text}

=== ТРЕБОВАНИЯ ===
Типы вариаций: {variant_types_str}
{forbid_str}
{invariant_str}

=== КРИТЕРИИ ===
- Сохрани сложность и количество операций
- Меняй только разрешённые элементы
- Ответ не должен совпадать с другими
- Не используй очевидные прогрессии

Выдай ТОЛЬКО текст варианта (без "ВАРИАНТ N:"):
"""

    system_prompt = "Ты — методист. Перегенерируешь один вариант задания."
    
    result = await call_llm(prompt, system_prompt)
    return result.strip()


# Генерация ответов для учителя
async def generate_answers(variants: Dict[int, str]) -> Dict[int, str]:
    """Генерирует ответы для всех вариантов."""
    
    variants_text = "\n\n".join([f"ВАРИАНТ {k}: {v}" for k, v in variants.items()])
    
    prompt = f"""
Реши каждое задание и верни ТОЛЬКО JSON с ответами.

=== ЗАДАНИЯ ===
{variants_text}

Формат:
{{
    "1": "ответ для варианта 1",
    "2": "ответ для варианта 2"
}}
"""

    try:
        result = await call_llm(prompt, expect_json=True)
        data = clean_json_response(result)
        return {int(k): v for k, v in data.items() if k.isdigit()}
    except Exception as e:
        logger.warning(f"Ошибка генерации ответов: {e}")
        return {}
