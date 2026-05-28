import httpx
import os
import json
import logging
import re
import uuid
import time
import hashlib
from typing import Optional
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any

load_dotenv()
logger = logging.getLogger(__name__)

GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

_cached_token: Optional[str] = None
_token_expires_at: float = 0


# HELPER: Авторизация в GigaChat
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
        _token_expires_at = time.time() + data.get("expires_in", 1800)
        
        logger.info(f"Получен новый Access Token")
        return _cached_token


def normalize_for_cache(text: str) -> str:
    """Нормализует текст для создания стабильного cache_key"""
    if not text:
        return ""
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    normalized = re.sub(r"[^\w\s]", "", normalized)
    return normalized


def sanitize_llm_text(text: str) -> str:
    """Убирает LaTeX-мусор из ответов LLM"""
    if not text:
        return text

    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$(.*?)\$', r'\1', text)

    replacements = {
        r'\\frac\{([^}]*)\}\{([^}]*)\}': r'(\1/\2)',
        r'\\sqrt\{([^}]*)\}': r'√(\1)',
        r'\\times': '×',
        r'\\cdot': '·',
        r'\\pm': '±',
        r'\\pi': 'π',
        r'\\neq': '≠',
        r'\\geq': '≥',
        r'\\leq': '≤',
        r'\\rightarrow': '→',
        r'\\leftarrow': '←',
    }

    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text)

    def fix_subscript(match):
        var = match.group(1)
        sub = match.group(2)
        if var in ['true', 'false', 'True', 'False']:
            return match.group(0)
        return f"{var}₍{sub}₎"
    
    text = re.sub(r'([a-zA-Z])_\{([^}]*)\}', fix_subscript, text)
    text = re.sub(r'([a-zA-Z0-9])\^2', r'\1²', text)
    text = re.sub(r'([a-zA-Z0-9])\^3', r'\1³', text)
    text = re.sub(r'([a-zA-Z0-9])\^(\d+)', r'\1^\2', text)
    text = re.sub(r'\\([a-zA-Z]+)', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\{(\d+)\}', r'\1', text)
    text = re.sub(r'\{\}', '', text)

    return text.strip()


async def call_llm(
    prompt: str, 
    system_prompt: str = None,
    expect_json: bool = False,
    temperature: float = 0.4
) -> str:
    """Базовый вызов GigaChat с авторизацией."""
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
        "temperature": temperature,
        "max_tokens": 4000
    }
    
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                response = await client.post(GIGACHAT_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                if "choices" not in data or not data["choices"]:
                    raise ValueError("Некорректный ответ LLM: нет choices")
                
                content = data["choices"][0]["message"]["content"]
                
                if expect_json:
                    return content
                return sanitize_llm_text(content)
                
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
    """Мок-ответ для демонстрации"""
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


def clean_json_response(result: str) -> dict:
    """парсинг JSON от LLM """
    if not result:
        raise ValueError("Пустой ответ от LLM")
    
    result = result.strip()
    
    result = re.sub(r'^```json\s*', '', result, flags=re.MULTILINE)
    result = re.sub(r'^```\s*', '', result, flags=re.MULTILINE)
    result = re.sub(r'\s*```$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^<json>\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\s*</json>$', '', result, flags=re.IGNORECASE)
    result = result.strip()
    
    depth = 0
    start_idx = -1
    end_idx = -1
    
    for i, ch in enumerate(result):
        if ch == '{':
            if depth == 0:
                start_idx = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start_idx != -1:
                end_idx = i
                break
    
    if start_idx != -1 and end_idx != -1:
        result = result[start_idx:end_idx + 1]
    else:
        json_match = re.search(r'(\{.*\})', result, re.DOTALL)
        if json_match:
            result = json_match.group(1)
        else:
            raise ValueError("JSON не найден в ответе LLM")
    
    result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', result)
    result = re.sub(r',\s*}', '}', result)
    result = re.sub(r',\s*]', ']', result)
    
    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        logger.warning(f"Ошибка парсинга JSON: {e}")
        logger.error(f"Не удалось распарсить JSON. Первые 500: {result[:500]}")
        raise ValueError(f"Некорректный JSON от LLM: {e}")


def _fix_latex_in_json(obj):
    """Восстанавливает LaTeX в строках JSON"""
    if isinstance(obj, dict):
        return {k: _fix_latex_in_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_fix_latex_in_json(item) for item in obj]
    elif isinstance(obj, str):
        obj = obj.replace('\x0c', '\\f')
        obj = obj.replace('\x08', '\\b')
        return obj
    else:
        return obj


def _stringify_answer_object(obj):
    """Превращает объект ответа в читаемую строку"""
    if obj is None:
        return "Нет ответа"
    
    if isinstance(obj, dict):
        for key in ['answer', 'value', 'text', 'result', 'ответ', 'результат', 'coefficients', 'type']:
            if key in obj and obj[key] is not None:
                val = obj[key]
                if isinstance(val, list):
                    return '; '.join(str(v) for v in val)
                return str(val)
        if 'coefficients' in obj and 'type' in obj:
            return f"коэф.: {obj['coefficients']}, тип: {obj['type']}"
        if 'coefficients' in obj:
            return str(obj['coefficients'])
        if 'type' in obj:
            return str(obj['type'])
        values = [str(v) for v in obj.values() if v is not None]
        return '; '.join(values) if values else str(obj)
    
    elif isinstance(obj, list):
        if all(isinstance(x, str) and len(x) == 1 and x.isalpha() for x in obj):
            return ', '.join(obj)
        return '; '.join(str(item) for item in obj)
    
    elif isinstance(obj, bool):
        return 'true' if obj else 'false'
    
    else:
        return str(obj)


def parse_structured_validation(response: str, variant_numbers: List[int]) -> Dict[str, Any]:
    """Парсит структурированный ответ валидации"""
    
    variant_status = {}
    answers = {}
    all_valid = True
    
    for num in variant_numbers:
        pattern = rf'\[VARIANT\s+{num}\](.*?)(?:\[VARIANT\s+\d+\]|$)'
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        
        if not match:
            variant_status[str(num)] = {
                "valid": False,
                "issues": ["Блок варианта не найден в ответе валидации"],
                "difficulty_match": True,
                "unique_answer": True,
                "same_structure": True,
                "solvable": True
            }
            answers[str(num)] = None
            all_valid = False
            continue
        
        block = match.group(1)
        
        status = {
            "valid": True,
            "solvable": True,
            "difficulty_match": True,
            "same_structure": True,
            "unique_answer": True,
            "issues": []
        }
        
        solvable_match = re.search(r'solvable\s*=\s*(true|false)', block, re.IGNORECASE)
        if solvable_match:
            status["solvable"] = solvable_match.group(1).lower() == "true"
            if not status["solvable"]:
                status["valid"] = False
        
        difficulty_match = re.search(r'difficulty_match\s*=\s*(true|false)', block, re.IGNORECASE)
        if difficulty_match:
            status["difficulty_match"] = difficulty_match.group(1).lower() == "true"
            if not status["difficulty_match"]:
                status["valid"] = False
        
        same_structure = re.search(r'same_structure\s*=\s*(true|false)', block, re.IGNORECASE)
        if same_structure:
            status["same_structure"] = same_structure.group(1).lower() == "true"
            if not status["same_structure"]:
                status["valid"] = False
        
        unique_answer = re.search(r'unique_answer\s*=\s*(true|false)', block, re.IGNORECASE)
        if unique_answer:
            status["unique_answer"] = unique_answer.group(1).lower() == "true"
            if not status["unique_answer"]:
                status["valid"] = False
        
        diff_reason = re.search(r'difficulty_mismatch_reason\s*=\s*(.+?)(?=\n\w+\s*=|\n*$)', block, re.IGNORECASE)
        if diff_reason and diff_reason.group(1).strip() != "none":
            status["difficulty_mismatch_reason"] = diff_reason.group(1).strip()
        
        struct_reason = re.search(r'structure_mismatch_reason\s*=\s*(.+?)(?=\n\w+\s*=|\n*$)', block, re.IGNORECASE)
        if struct_reason and struct_reason.group(1).strip() != "none":
            status["structure_mismatch_reason"] = struct_reason.group(1).strip()
        
        issues_match = re.search(r'issues\s*=\s*(.+?)(?=\n\w+\s*=|\n*$)', block, re.IGNORECASE)
        if issues_match:
            issues_text = issues_match.group(1).strip()
            if issues_text != "none":
                status["issues"] = [issues_text]
                status["valid"] = False
        
        answer_match = re.search(r'answer\s*=\s*(.+?)(?=\n\w+\s*=|\n*$)', block, re.IGNORECASE)
        if answer_match:
            answers[str(num)] = answer_match.group(1).strip()
        else:
            answers[str(num)] = None
        
        if not status["valid"]:
            all_valid = False
        
        variant_status[str(num)] = status
    
    total = len(variant_numbers)
    valid_count = sum(1 for s in variant_status.values() if s.get("valid", False))
    invalid_count = total - valid_count
    
    issues_by_type = {
        "solvable": sum(1 for s in variant_status.values() if not s.get("solvable", True)),
        "difficulty": sum(1 for s in variant_status.values() if not s.get("difficulty_match", True)),
        "structure": sum(1 for s in variant_status.values() if not s.get("same_structure", True)),
        "uniqueness": sum(1 for s in variant_status.values() if not s.get("unique_answer", True))
    }

    for num, answer in answers.items():
        if isinstance(answer, dict):
            for key in ['answer', 'value', 'text', 'result', 'ответ']:
                if key in answer and answer[key]:
                    answers[num] = str(answer[key])
                    break
            else:
                answers[num] = str(answer) if answer else None
        elif isinstance(answer, list):
            answers[num] = '; '.join(str(a) for a in answer) if answer else None
        elif answer is None:
            answers[num] = None
    
    return {
        "valid": all_valid,
        "variant_status": variant_status,
        "answers": answers,
        "summary": {
            "total": total,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "warning_count": invalid_count,
            "issues_by_type": issues_by_type
        }
    }