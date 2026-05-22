from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from database import SessionLocal, Task, GeneratedVariant
from file_parser import parse_file
from llm_service import (
    analyze_task_structure,
    generate_variants,
    validate_variants,
    regenerate_variant as llm_regenerate_variant,
    generate_answers
)
from rate_limiter import rate_limiter
from export_service import export_to_pdf, export_to_docx
from models import EditVariantRequest, ExportRequest, RegenerateVariantRequest
import json
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(title="TaskForge AI API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def normalize_task_structure(structure: dict) -> dict:
    """Приводит task_structure к правильному формату"""
    normalized = structure.copy()
    
    if isinstance(normalized.get("task_type"), list):
        normalized["task_type"] = normalized["task_type"][0] if normalized["task_type"] else "не определён"
    
    if isinstance(normalized.get("subject"), list):
        normalized["subject"] = normalized["subject"][0] if normalized["subject"] else "не определён"
    
    if isinstance(normalized.get("difficulty_score"), list):
        normalized["difficulty_score"] = normalized["difficulty_score"][0] if normalized["difficulty_score"] else 5
    
    if isinstance(normalized.get("operations_count"), list):
        normalized["operations_count"] = normalized["operations_count"][0] if normalized["operations_count"] else 3
    
    if not isinstance(normalized.get("difficulty_score"), (int, float)):
        normalized["difficulty_score"] = 5
    if not isinstance(normalized.get("operations_count"), (int, float)):
        normalized["operations_count"] = 3
    
    return normalized

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# HELPER: работа с task_structure (JSON ↔ Text)
def _save_task_structure(task_structure: dict) -> str:
    """Преобразует dict в JSON строку для сохранения в БД"""
    if task_structure is None:
        return None
    return json.dumps(task_structure, ensure_ascii=False)


def _load_task_structure(task_structure_str: str) -> dict:
    """Преобразует JSON строку из БД в dict"""
    if task_structure_str is None:
        return None
    if isinstance(task_structure_str, dict):  # уже dict (например, из SQLite JSON типа)
        return task_structure_str
    try:
        return json.loads(task_structure_str)
    except (json.JSONDecodeError, TypeError):
        return None


# HEALTH CHECK
@app.get("/")
def root():
    return {"message": "TaskForge AI API работает", "status": "ok"}


# ОСНОВНОЙ ЭНДПОИНТ: ЗАГРУЗКА + ГЕНЕРАЦИЯ
@app.post("/upload-and-generate")
async def upload_and_generate(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    num_variants: int = Form(4),
    variation_types: str = Form("numbers,order"),
    forbidden_parts: str = Form(None),
    difficulty_override: str = Form("same"),
    target_grade: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Загружает файл, парсит, анализирует структуру и генерирует варианты.
    """
    # 1. Проверка лимита
    if not rate_limiter.can_request(session_id):
        raise HTTPException(
            status_code=429, 
            detail=f"Превышен лимит: {rate_limiter.max_requests} запросов в час"
        )
    
    # 2. Валидация количества вариантов
    if num_variants < 2 or num_variants > 10:
        raise HTTPException(
            status_code=400, 
            detail="Количество вариантов должно быть от 2 до 10"
        )
    
    # 3. Проверка размера файла
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Файл превышает {MAX_FILE_SIZE // (1024*1024)} MB"
        )
    
    # 4. Парсинг файла
    try:
        parsed_text = parse_file(content, file.filename)
        if not parsed_text or not parsed_text.strip():
            raise HTTPException(
                status_code=400, 
                detail="Не удалось извлечь текст из файла"
            )
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Ошибка парсинга: {str(e)}"
        )
    
    logger.info(f"Файл распарсен, длина текста: {len(parsed_text)} символов")
    
    # 5. Анализ структуры задания (через LLM)
    try:
        task_structure = await analyze_task_structure(parsed_text)
        task_structure = normalize_task_structure(task_structure)

        logger.info(f"Анализ структуры: {task_structure.get('task_type')}, "
                   f"сложность {task_structure.get('difficulty_score')}")
    except Exception as e:
        logger.warning(f"Ошибка анализа структуры: {e}")
        task_structure = {
            "subject": "не определён",
            "task_type": "не определён",
            "difficulty_score": 5,
            "operations_count": 3,
            "grade": "5-9",
            "variable_elements": ["числа", "параметры"],
            "invariant_elements": ["структура", "алгоритм решения"],
            "recommended_variations": ["numbers", "order"],
            "why_difficulty": "Стандартный уровень",
            "why_invariant": "Методически важно сохранить структуру",
            "why_variable": "Числовые значения могут варьироваться"
        }
    
    # 6. Сохраняем задание в БД (преобразуем task_structure в JSON строку)
    task = Task(
        session_id=session_id,
        original_text=parsed_text[:500],
        parsed_text=parsed_text,
        task_structure=_save_task_structure(task_structure),
        difficulty_override=difficulty_override,
        target_grade=target_grade
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 7. Генерация вариантов
    variation_list = [v.strip() for v in variation_types.split(",")]
    
    try:
        variants = await generate_variants(
            original_text=parsed_text,
            num_variants=num_variants,
            variation_types=variation_list,
            forbidden_parts=forbidden_parts,
            task_structure=task_structure,
            difficulty_override=difficulty_override,
            target_grade=target_grade
        )
        logger.info(f"Сгенерировано {len(variants)} вариантов")
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")
    
    # 8. Валидация сгенерированных вариантов
    try:
        validation = await validate_variants(
            variants=variants,
            original_text=parsed_text,
            task_structure=task_structure
        )
        #answers = await generate_answers(variants)
        #validation["answers"] = answers
        logger.info(f"Валидация: valid={validation.get('valid')}")
        
        # Применяем исправления от LLM (если есть)
        fixed_variants = validation.get("fixed_variants", {})
        if fixed_variants:
            for num, fixed_text in fixed_variants.items():
                if fixed_text:
                    variants[int(num)] = fixed_text
                    logger.info(f"Вариант {num} исправлен")
    except Exception as e:
        logger.warning(f"Ошибка валидации: {e}")
        validation = {
            "valid": True,
            "difficulty_match": True,
            "unique_answers": True,
            "same_structure": True,
            "all_solvable": True,
            "issues": ["Валидация пропущена"],
            "explanations": {},
            "answers": {},
            "fixed_variants": {}
        }
    
    # 9. Сохраняем варианты в БД
    for v_num, content_text in variants.items():
        difficulty_val = task_structure.get("difficulty_score", 5)
        if isinstance(difficulty_val, list):
            difficulty_val = difficulty_val[0] if difficulty_val else 5
        elif not isinstance(difficulty_val, (int, float)):
            difficulty_val = 5
        
        variant = GeneratedVariant(
            session_id=session_id,
            task_id=task.id,
            variant_number=v_num,
            content=content_text,
            edited_content=content_text,
            difficulty_score=int(difficulty_val)
        )
        db.add(variant)
    db.commit()
    
    # 10. Формируем ответ (task_structure возвращаем как dict)
    return JSONResponse({
        "task_id": task.id,
        "variants": variants,
        "task_structure": task_structure,
        "validation": validation,
        "difficulty_override": difficulty_override,
        "target_grade": target_grade,
        "message": f"Сгенерировано {len(variants)} вариантов"
    })


# ПЕРЕГЕНЕРАЦИЯ ОДНОГО ВАРИАНТА
@app.post("/regenerate-variant")
async def regenerate_variant_endpoint(
    request: RegenerateVariantRequest,
    db: Session = Depends(get_db)
):
    """  Перегенерирует конкретный вариант """
    if not rate_limiter.can_request(request.session_id):
        raise HTTPException(status_code=429, detail="Превышен лимит запросов")
    
    # Получаем задание
    task = db.query(Task).filter(
        Task.session_id == request.session_id,
        Task.id == request.task_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    # Получаем текущий вариант
    variant = db.query(GeneratedVariant).filter(
        GeneratedVariant.session_id == request.session_id,
        GeneratedVariant.task_id == request.task_id,
        GeneratedVariant.variant_number == request.variant_number
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Вариант не найден")
    
    # Загружаем task_structure из JSON строки
    task_structure = _load_task_structure(task.task_structure)
    
    # Генерируем новый вариант
    try:
        new_content = await llm_regenerate_variant(
            original_text=task.parsed_text,
            variant_number=request.variant_number,
            current_variant_text=variant.content,
            variation_types=["numbers", "order"],
            task_structure=task_structure,
            forbidden_parts=None
        )
        
        # Обновляем в БД
        variant.content = new_content
        variant.edited_content = new_content
        db.commit()
        
        logger.info(f"Вариант {request.variant_number} перегенерирован")
        
        return {
            "variant_number": request.variant_number,
            "content": new_content,
            "message": "Вариант перегенерирован"
        }
    except Exception as e:
        logger.error(f"Ошибка перегенерации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка перегенерации: {str(e)}")


# РЕДАКТИРОВАНИЕ ВАРИАНТА
@app.post("/edit-variant")
async def edit_variant(
    request: EditVariantRequest,
    db: Session = Depends(get_db)
):
    """ Сохраняет отредактированный вариант """
    variant = db.query(GeneratedVariant).filter(
        GeneratedVariant.session_id == request.session_id,
        GeneratedVariant.task_id == request.task_id,
        GeneratedVariant.variant_number == request.variant_number
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Вариант не найден")
    
    variant.edited_content = request.edited_content
    db.commit()
    
    logger.info(f"Вариант {request.variant_number} сохранён")
    
    return {"message": "Вариант сохранён"}


# ЭКСПОРТ
@app.post("/export")
async def export(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """ Экспортирует варианты в PDF или DOCX """
    variants = db.query(GeneratedVariant).filter(
        GeneratedVariant.session_id == request.session_id,
        GeneratedVariant.task_id == request.task_id
    ).order_by(GeneratedVariant.variant_number).all()
    
    if not variants:
        raise HTTPException(status_code=404, detail="Варианты не найдены")
    
    content_list = [
        f"ВАРИАНТ {v.variant_number}\n\n{(v.edited_content or v.content)}" 
        for v in variants
    ]
    
    if request.format == "pdf":
        try:
            buffer = export_to_pdf(content_list)
            media_type = "application/pdf"
            filename = f"task_{request.task_id}.pdf"
        except Exception as e:
            logger.error(f"Ошибка PDF экспорта: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка PDF: {str(e)}")
    elif request.format == "docx":
        try:
            buffer = export_to_docx(content_list)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"task_{request.task_id}.docx"
        except Exception as e:
            logger.error(f"Ошибка DOCX экспорта: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка DOCX: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Формат должен быть pdf или docx")
    
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ИСТОРИЯ ЗАДАНИЙ
@app.get("/history/{session_id}")
async def get_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """ Возвращает список всех заданий пользователя """
    tasks = db.query(Task).filter(
        Task.session_id == session_id
    ).order_by(Task.created_at.desc()).all()
    
    return {
        "tasks": [
            {
                "task_id": t.id,
                "created_at": t.created_at.isoformat(),
                "preview": t.original_text[:100] if t.original_text else "Нет текста",
                "difficulty_override": t.difficulty_override,
                "target_grade": t.target_grade
            }
            for t in tasks
        ]
    }

# ПОЛУЧЕНИЕ ВАРИАНТОВ ЗАДАНИЯ
@app.get("/get-variants/{session_id}/{task_id}")
async def get_variants(
    session_id: str,
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    Возвращает все варианты конкретного задания.
    """
    variants = db.query(GeneratedVariant).filter(
        GeneratedVariant.session_id == session_id,
        GeneratedVariant.task_id == task_id
    ).order_by(GeneratedVariant.variant_number).all()
    
    if not variants:
        raise HTTPException(status_code=404, detail="Варианты не найдены")
    
    return {
        "task_id": task_id,
        "variants": {
            v.variant_number: v.edited_content or v.content
            for v in variants
        }
    }

# АНАЛИЗ СЛОЖНОСТИ (по session_id + task_id)
@app.get("/analyze-difficulty/{session_id}/{task_id}")
async def get_difficulty_analysis(
    session_id: str,
    task_id: int,
    db: Session = Depends(get_db)
):
    """ Возвращает анализ сложности задания """
    task = db.query(Task).filter(
        Task.session_id == session_id,
        Task.id == task_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    # Загружаем task_structure из JSON строки
    task_structure = _load_task_structure(task.task_structure)
    
    return {
        "task_id": task.id,
        "task_structure": task_structure,
        "difficulty_override": task.difficulty_override,
        "target_grade": task.target_grade
    }


# ОЧИСТКА СЕССИИ
@app.delete("/clear-session/{session_id}")
def clear_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """ Удаляет все данные пользователя """
    db.query(GeneratedVariant).filter(
        GeneratedVariant.session_id == session_id
    ).delete()
    db.query(Task).filter(Task.session_id == session_id).delete()
    db.commit()
    
    return {"message": "Данные сессии удалены"}


# ЛИМИТЫ ЗАПРОСОВ
@app.get("/rate-limit/{session_id}")
def get_rate_limit(session_id: str):
    """
    Возвращает информацию о лимите запросов.
    """
    return {
        "remaining": rate_limiter.remaining_requests(session_id),
        "max_per_hour": rate_limiter.max_requests
    }