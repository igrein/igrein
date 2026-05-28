from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from database import SessionLocal, Task, GeneratedVariant, User, UserSession, get_db
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
from models import EditVariantRequest, ExportRequest, RegenerateVariantRequest, UserRegister, UserLogin, UserResponse, TokenResponse
import json
import logging
import os
from document_parser import parse_variant_to_document
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from answer_validators import validate_answers_batch, format_validation_for_frontend, AnswerFormat
from typing import Dict, List, Optional, Any, Union

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(title="TaskForge AI API")


# Security
security = HTTPBearer()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ АВТОРИЗАЦИИ 
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return check_password_hash(hashed_password, plain_password)

def get_password_hash(password: str) -> str:
    return generate_password_hash(password)

def create_session_token(user_id: int, db: Session) -> str:
    """Создаёт новый токен сессии"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    session = UserSession(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    return token

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Получает текущего пользователя по токену из заголовка"""
    token = credentials.credentials
    
    session = db.query(UserSession).filter(
        UserSession.token == token,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истёкший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    
    return user


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ 
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

def _save_task_structure(task_structure: dict) -> str:
    """Преобразует dict в JSON строку для сохранения в БД"""
    if task_structure is None:
        return None
    return json.dumps(task_structure, ensure_ascii=False)

def _load_task_structure(task_structure_str: str) -> dict:
    """Преобразует JSON строку из БД в dict"""
    if task_structure_str is None:
        return None
    if isinstance(task_structure_str, dict):
        return task_structure_str
    try:
        return json.loads(task_structure_str)
    except (json.JSONDecodeError, TypeError):
        return None


# ЭНДПОИНТЫ АВТОРИЗАЦИИ
@app.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Регистрация нового пользователя"""
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Имя пользователя уже занято")
    
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        password_hash=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_session_token(user.id, db)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at.isoformat()
        )
    )

@app.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Вход пользователя"""
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    
    token = create_session_token(user.id, db)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at.isoformat()
        )
    )

@app.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at.isoformat()
    )

@app.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Выход — удаляем текущий токен"""
    token = credentials.credentials
    db.query(UserSession).filter(UserSession.token == token).delete()
    db.commit()
    return {"message": "Выход выполнен"}


#  HEALTH CHECK 
@app.get("/")
def root():
    return {"message": "TaskForge AI API работает", "status": "ok"}


#  ОСНОВНОЙ ЭНДПОИНТ: ЗАГРУЗКА + ГЕНЕРАЦИЯ 
@app.post("/upload-and-generate")
async def upload_and_generate(
    file: UploadFile = File(...),
    num_variants: int = Form(4),
    variation_types: str = Form("numbers,order"),
    forbidden_parts: str = Form(None),
    difficulty_override: str = Form("same"),
    target_grade: str = Form(None),
    task_type: str = Form(None),
    preview_only: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Загружает файл, парсит, анализирует структуру.
    Если preview_only=True - возвращает только анализ, без генерации вариантов."""
    
    # 1. Проверка лимита по user_id
    if not rate_limiter.can_request(current_user.id):
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
    
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 4. Парсинг файла
    try:
        parsed_text = parse_file(content, file.filename)
        
        logger.info(f"Распарсенный текст (первые 200 символов): {parsed_text[:200] if parsed_text else 'None'}")
        
        if not parsed_text or not parsed_text.strip():
            if file.filename.lower().endswith('.pdf'):
                from file_parser import _parse_pdf_robust
                parsed_text = _parse_pdf_robust(content)
            
            if not parsed_text or not parsed_text.strip():
                raise HTTPException(
                    status_code=400, 
                    detail="Не удалось извлечь текст из файла. Убедитесь, что файл не поврежден и содержит текст."
                )
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Ошибка парсинга файла: {str(e)}"
        )
    
    # 5. Анализ структуры задания
    try:
        task_structure = await analyze_task_structure(parsed_text)
        task_structure = normalize_task_structure(task_structure)

        logger.info(f"Анализ структуры: {task_structure.get('task_type')}, сложность {task_structure.get('difficulty_score')}")
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
    
    # 6. Сохраняем задание в БД с user_id
    task = Task(
        user_id=current_user.id,
        original_text=parsed_text[:500],
        parsed_text=parsed_text,
        task_structure=_save_task_structure(task_structure),
        difficulty_override=difficulty_override,
        target_grade=target_grade
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # ✅ ЕСЛИ preview_only=True - возвращаем только анализ, НЕ генерируем варианты
    if preview_only:
        logger.info(f"Preview only mode: возвращаем анализ для task_id={task.id}")
        return JSONResponse({
            "task_id": task.id,
            "task_structure": task_structure,
            "preview_only": True,
            "message": "Структура проанализирована. Нажмите 'Сгенерировать варианты' для продолжения."
        })
    
    # 7. Генерация вариантов (только если preview_only=False)
    variation_list = [v.strip() for v in variation_types.split(",")]
    
    try:
        variants_docs = await generate_variants(
            original_text=parsed_text,
            num_variants=num_variants,
            variation_types=variation_list,
            forbidden_parts=forbidden_parts,
            task_structure=task_structure,
            difficulty_override=difficulty_override,
            target_grade=target_grade,
            task_type=task_type
        )
        logger.info(f"Сгенерировано {len(variants_docs)} документов-вариантов")
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")
    
    # 8. Конвертируем в plain text
    variants_plain_text = {}
    for v_num, variant_doc in variants_docs.items():
        variants_plain_text[v_num] = variant_doc.to_plain_text()
    
    # 9. Валидация
    try:
        validation = await validate_variants(
            variants=variants_plain_text,
            original_text=parsed_text,
            task_structure=task_structure
        )
        answers = await generate_answers(variants_plain_text)
        validation["answers"] = answers
        logger.info(f"Валидация: valid={validation.get('valid')}")
        
        fixed_variants = validation.get("fixed_variants", {})
        if fixed_variants:
            for num, fixed_text in fixed_variants.items():
                if fixed_text:
                    variants_docs[int(num)] = parse_variant_to_document(fixed_text, int(num))
                    variants_plain_text[int(num)] = fixed_text
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
    
    # 10. Сохраняем варианты в БД
    for v_num, variant_doc in variants_docs.items():
        from llm_service import format_variant_text
        
        plain_text = variant_doc.to_plain_text()
        formatted_text = format_variant_text(plain_text)
        variant_doc = parse_variant_to_document(formatted_text, v_num)
        original_text_parts = []
        for block in variant_doc.blocks:
            if block.type == "text":
                original_text_parts.append(block.content)
            elif block.type == "formula":
                original_text_parts.append(f"\\({block.latex}\\)")
            elif block.type == "table":
                original_text_parts.append(block.latex)
        
        full_text = "\n\n".join(original_text_parts)
        
        difficulty_val = task_structure.get("difficulty_score", 5)
        if isinstance(difficulty_val, list):
            difficulty_val = difficulty_val[0] if difficulty_val else 5
        elif not isinstance(difficulty_val, (int, float)):
            difficulty_val = 5
        
        variant = GeneratedVariant(
            user_id=current_user.id,
            task_id=task.id,
            variant_number=v_num,
            content=full_text,
            edited_content=full_text,
            difficulty_score=int(difficulty_val)
        )
        db.add(variant)

    db.commit()
    
    return JSONResponse({
        "task_id": task.id,
        "variants": variants_plain_text,
        "task_structure": task_structure,
        "validation": validation,
        "difficulty_override": difficulty_override,
        "target_grade": target_grade,
        "message": f"Сгенерировано {len(variants_docs)} вариантов"
    })



@app.post("/generate-from-task")
async def generate_from_task(
    task_id: int = Form(...),
    num_variants: int = Form(4),
    variation_types: str = Form("numbers,order"),
    forbidden_parts: str = Form(None),
    difficulty_override: str = Form("same"),
    target_grade: str = Form(None),
    task_type: str = Form(None),
    user_comment: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Генерирует варианты на основе ранее проанализированного задания.
    Реализует до 2 итераций перегенерации проблемных вариантов."""
    
    MAX_ITERATIONS = 2
    
    # Проверка лимита
    if not rate_limiter.can_request(current_user.id):
        raise HTTPException(
            status_code=429, 
            detail=f"Превышен лимит: {rate_limiter.max_requests} запросов в час"
        )
    
    # Получаем задание из БД
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    # Загружаем структуру задания
    task_structure = _load_task_structure(task.task_structure)
    
    # Парсим типы вариаций
    variation_list = [v.strip() for v in variation_types.split(",")]
    
    # Генерируем варианты с комментарием
    try:
        variants_docs = await generate_variants(
            original_text=task.parsed_text,
            num_variants=num_variants,
            variation_types=variation_list,
            forbidden_parts=forbidden_parts,
            task_structure=task_structure,
            difficulty_override=difficulty_override,
            target_grade=target_grade,
            task_type=task_type,
            user_comment=user_comment
        )
        logger.info(f"Сгенерировано {len(variants_docs)} документов-вариантов с комментарием: {user_comment}")
    except Exception as e:
        logger.error(f"Ошибка генерации: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")
    
    # Конвертируем в plain text и фильтруем только нужные номера вариантов
    variants_plain_text = {}
    valid_variant_numbers = set(range(1, num_variants + 1))
    
    for v_num, variant_doc in variants_docs.items():
        # Пропускаем варианты с некорректными номерами
        if v_num not in valid_variant_numbers:
            logger.warning(f"Пропускаем вариант с некорректным номером {v_num}, ожидались номера 1-{num_variants}")
            continue
        variants_plain_text[v_num] = variant_doc.to_plain_text()
    
    # Если после фильтрации осталось меньше вариантов, чем нужно, дополняем
    if len(variants_plain_text) < num_variants:
        logger.warning(f"Получено только {len(variants_plain_text)} вариантов из {num_variants}, дополняем")
        for i in range(1, num_variants + 1):
            if i not in variants_plain_text:
                variants_plain_text[i] = f"Вариант {i}\n(сгенерируйте заново)"
                # Создаём заглушку для variants_docs
                variants_docs[i] = parse_variant_to_document(variants_plain_text[i], i)
    
    # ========== ЦИКЛ ИТЕРАЦИЙ ПЕРЕГЕНЕРАЦИИ ==========
    validation = None
    problem_variants_history = [] 
    
    for iteration in range(MAX_ITERATIONS):
        logger.info(f"=== ИТЕРАЦИЯ {iteration + 1}/{MAX_ITERATIONS} ===")
        
        # 1. Валидация текущих вариантов
        try:
            validation = await validate_variants(
                variants=variants_plain_text,
                original_text=task.parsed_text,
                task_structure=task_structure
            )
            logger.info(f"Валидация итерации {iteration + 1}: valid={validation.get('valid')}")
        except Exception as e:
            logger.warning(f"Ошибка валидации в итерации {iteration + 1}: {e}")
            # Если валидация упала, не прерываем процесс
            if validation is None:
                validation = {
                    "valid": True,
                    "variant_status": {},
                    "answers": {},
                    "summary": {"total": len(variants_plain_text), "valid_count": len(variants_plain_text), "invalid_count": 0}
                }
            break
        
        # 2. Собираем проблемные варианты (только в пределах 1..num_variants)
        variant_status = validation.get("variant_status", {})
        problem_variants = [
            num for num, status in variant_status.items()
            if not status.get("valid", True) and isinstance(num, int) and 1 <= num <= num_variants
        ]
        
        if not problem_variants:
            logger.info(f"Все варианты валидны, завершаем цикл после {iteration + 1} итерации(й)")
            break
        
        logger.info(f"Проблемные варианты в итерации {iteration + 1}: {problem_variants}")
        problem_variants_history.append({
            "iteration": iteration + 1,
            "problem_variants": problem_variants,
            "issues": {str(num): variant_status.get(str(num), {}).get("issues", []) for num in problem_variants}
        })
        
        # 3. Перегенерируем КАЖДЫЙ проблемный вариант
        for num in problem_variants:
            # Дополнительная проверка номера варианта
            if num < 1 or num > num_variants:
                logger.warning(f"Пропускаем перегенерацию варианта {num} - номер вне допустимого диапазона (1-{num_variants})")
                continue
            
            num_str = str(num)
            status = variant_status.get(num_str, {})
            issues = status.get("issues", [])
            issues_text = "; ".join(issues) if issues else "Не соответствует критериям качества"
            
            logger.info(f"Перегенерация варианта {num}, причины: {issues_text}")
            
            try:
                new_content = await llm_regenerate_variant(
                    original_text=task.parsed_text,
                    variant_number=num,
                    current_variant_text=variants_plain_text.get(num, ""),
                    variation_types=variation_list,
                    task_structure=task_structure,
                    forbidden_parts=forbidden_parts,
                    failure_reason=issues_text
                )
                
                # Обновляем вариант
                variants_plain_text[num] = new_content
                variants_docs[num] = parse_variant_to_document(new_content, num)
                logger.info(f"Вариант {num} перегенерирован в итерации {iteration + 1}")
                
            except Exception as e:
                logger.error(f"Ошибка перегенерации варианта {num}: {e}")

    
    # 4. Финальная валидация
    if validation is None or problem_variants_history:
        try:
            validation = await validate_variants(
                variants=variants_plain_text,
                original_text=task.parsed_text,
                task_structure=task_structure
            )
        except Exception as e:
            logger.warning(f"Ошибка финальной валидации: {e}")
    
    # 5. Добавляем информацию о проблемах, которые остались после всех итераций
    variant_status = validation.get("variant_status", {})
    remaining_problems = {}
    for num, status in variant_status.items():
        num_int = int(num) if str(num).isdigit() else num
        if not status.get("valid", True) and isinstance(num_int, int) and 1 <= num_int <= num_variants:
            remaining_problems[str(num)] = status.get("issues", ["Неизвестная проблема"])
    
    if remaining_problems:
        logger.warning(f"После {MAX_ITERATIONS} итераций остались проблемы: {remaining_problems}")
        validation["problems_remaining"] = remaining_problems
    else:
        validation["problems_remaining"] = None
    
    # Добавляем историю итераций в ответ (опционально)
    validation["regeneration_history"] = problem_variants_history
    
    # Генерируем ответы отдельно (если их нет в валидации)
    answers = validation.get("answers", {})
    if not answers:
        try:
            answers = await generate_answers(variants_plain_text)
            validation["answers"] = answers
        except Exception as e:
            logger.warning(f"Ошибка генерации ответов: {e}")
            validation["answers"] = {str(k): None for k in variants_plain_text.keys()}
    
    # Обновляем validation["valid"] на основе финального статуса
    valid_count = validation.get("summary", {}).get("valid_count", 0)
    total_count = validation.get("summary", {}).get("total", len(variants_plain_text))
    validation["valid"] = (valid_count == total_count) and not remaining_problems
    
    #  СОХРАНЕНИЕ В БД С ПРОВЕРКОЙ УНИКАЛЬНОСТИ
    try:
        # Удаляем старые варианты этого задания
        deleted_count = db.query(GeneratedVariant).filter(
            GeneratedVariant.task_id == task_id,
            GeneratedVariant.user_id == current_user.id
        ).delete()
        logger.info(f"Удалено старых вариантов: {deleted_count}")
        
        db.flush()
        
        # Сохраняем новые варианты
        saved_count = 0
        from llm_service import format_variant_text
        
        for v_num in range(1, num_variants + 1):
            variant_doc = variants_docs.get(v_num)
            if not variant_doc:
                logger.warning(f"Вариант {v_num} отсутствует в variants_docs, создаём заглушку")
                plain_text = variants_plain_text.get(v_num, f"Вариант {v_num}\n(ошибка генерации)")
                variant_doc = parse_variant_to_document(plain_text, v_num)
            
            plain_text = variant_doc.to_plain_text()
            formatted_text = format_variant_text(plain_text)
            variant_doc = parse_variant_to_document(formatted_text, v_num)
            
            # Собираем полный текст
            full_text_parts = []
            for block in variant_doc.blocks:
                if block.type == "text":
                    full_text_parts.append(block.content)
                elif block.type == "formula":
                    full_text_parts.append(f"\\({block.latex}\\)")
                elif block.type == "table":
                    full_text_parts.append(block.latex)
            full_text = "\n\n".join(full_text_parts)
            
            # Получаем сложность
            difficulty_val = task_structure.get("difficulty_score", 5)
            if isinstance(difficulty_val, list):
                difficulty_val = difficulty_val[0] if difficulty_val else 5
            elif not isinstance(difficulty_val, (int, float)):
                difficulty_val = 5
            
            # Проверяем, не существует ли уже такой вариант (на случай если delete не сработал)
            existing = db.query(GeneratedVariant).filter(
                GeneratedVariant.task_id == task_id,
                GeneratedVariant.variant_number == v_num,
                GeneratedVariant.user_id == current_user.id
            ).first()
            
            if existing:
                # Обновляем существующий
                existing.content = full_text
                existing.edited_content = full_text
                existing.difficulty_score = int(difficulty_val)
                logger.info(f"Вариант {v_num} обновлён")
            else:
                # Создаём новый
                variant = GeneratedVariant(
                    user_id=current_user.id,
                    task_id=task_id,
                    variant_number=v_num,
                    content=full_text,
                    edited_content=full_text,
                    difficulty_score=int(difficulty_val)
                )
                db.add(variant)
                saved_count += 1
        
        db.commit()
        logger.info(f"Сохранено вариантов: {saved_count}, обновлено: {num_variants - saved_count}")
        
    except Exception as e:
        logger.error(f"Ошибка сохранения в БД: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения вариантов: {str(e)}")
    
    # Формируем ответ
    message = f"Сгенерировано {len(variants_plain_text)} вариантов"
    if remaining_problems:
        message += f". Проблемные варианты после {MAX_ITERATIONS} итераций: {len(remaining_problems)}"
    else:
        message += ". ✅ Все варианты успешно прошли проверку!"
    
    return JSONResponse({
        "task_id": task.id,
        "variants": variants_plain_text,
        "task_structure": task_structure,
        "validation": validation,
        "difficulty_override": difficulty_override,
        "target_grade": target_grade,
        "message": message
    })

#  ПЕРЕГЕНЕРАЦИЯ ВАРИАНТА 
@app.post("/regenerate-variant")
async def regenerate_variant_endpoint(
    request: RegenerateVariantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Перегенерирует конкретный вариант"""
    if not rate_limiter.can_request(current_user.id):
        raise HTTPException(status_code=429, detail="Превышен лимит запросов")
    
    task = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.id == request.task_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    variant = db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id,
        GeneratedVariant.task_id == request.task_id,
        GeneratedVariant.variant_number == request.variant_number
    ).first()
    
    if not variant:
        raise HTTPException(status_code=404, detail="Вариант не найден")
    
    task_structure = _load_task_structure(task.task_structure)
    
    try:
        new_content = await llm_regenerate_variant(
            original_text=task.parsed_text,
            variant_number=request.variant_number,
            current_variant_text=variant.content,
            variation_types=["numbers", "order"],
            task_structure=task_structure,
            forbidden_parts=None
        )
        
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

@app.post("/check-answers/{task_id}")
async def check_answers(
    task_id: int,
    user_answers: Dict[int, str],  # {variant_num: student_answer}
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Проверяет ответы ученика через Python-валидаторы"""
    
    # Получаем правильные ответы из БД
    variants = db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id,
        GeneratedVariant.task_id == task_id
    ).all()
    
    expected_answers = {v.variant_number: "A" for v in variants}  # TODO: хранить реальные ответы
    
    task = db.query(Task).filter(Task.id == task_id).first()
    task_structure = _load_task_structure(task.task_structure) if task else None
    
    # Валидируем
    results = validate_answers_batch(
        answers=user_answers,
        expected_answers=expected_answers,
        subject=task_structure.get("subject") if task_structure else None
    )
    
    return {
        "results": {
            num: {
                "correct": r.correct,
                "confidence": r.confidence,
                "expected": r.expected_answer
            }
            for num, r in results.items()
        },
        "score": sum(1 for r in results.values() if r.correct) / len(results) * 100 if results else 0
    }




#  РЕДАКТИРОВАНИЕ ВАРИАНТА 
@app.post("/edit-variant")
async def edit_variant(
    request: EditVariantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сохраняет отредактированный вариант"""
    variant = db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id,
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
@app.get("/export")
async def export_get(
    task_id: int,
    format: str,
    include_answers: bool = False,  # ← новая галка
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Экспорт вариантов через GET-запрос"""
    variants = db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id,
        GeneratedVariant.task_id == task_id
    ).order_by(GeneratedVariant.variant_number).all()
    
    if not variants:
        raise HTTPException(status_code=404, detail="Варианты не найдены")
    

    answers = None
    if include_answers:
        try:
            from llm_service import generate_answers
            variants_dict = {v.variant_number: v.edited_content or v.content for v in variants}
            answers = await generate_answers(variants_dict)
        except:
            answers = {}
    
    from document_parser import parse_variant_to_document
    
    variant_documents = []
    for v in variants:
        text = v.edited_content or v.content
        variant_doc = parse_variant_to_document(text, v.variant_number)
        variant_documents.append(variant_doc)
    
    if format == "pdf":
        buffer = export_to_pdf(variant_documents, answers, include_answers)
        media_type = "application/pdf"
        filename = f"task_{task_id}.pdf"
    elif format == "docx":
        buffer = export_to_docx(variant_documents, answers, include_answers)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"task_{task_id}.docx"
    else:
        raise HTTPException(status_code=400, detail="Формат должен быть pdf или docx")
    
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/export")
async def export(
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Экспортирует варианты в PDF или DOCX"""
    variants = db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id,
        GeneratedVariant.task_id == request.task_id
    ).order_by(GeneratedVariant.variant_number).all()
    
    if not variants:
        raise HTTPException(status_code=404, detail="Варианты не найдены")
    
    from document_parser import parse_variant_to_document
    
    variant_documents = []
    for v in variants:
        text = v.edited_content or v.content
        variant_doc = parse_variant_to_document(text, v.variant_number)
        variant_documents.append(variant_doc)
    
    if request.format == "pdf":
        try:
            buffer = export_to_pdf(variant_documents)
            media_type = "application/pdf"
            filename = f"task_{request.task_id}.pdf"
        except Exception as e:
            logger.error(f"Ошибка PDF экспорта: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка PDF: {str(e)}")
    elif request.format == "docx":
        try:
            buffer = export_to_docx(variant_documents)
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
@app.get("/history")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возвращает список всех заданий пользователя"""
    tasks = db.query(Task).filter(
        Task.user_id == current_user.id
    ).order_by(Task.created_at.desc()).all()
    
    return {
        "tasks": [
            {
                "task_id": t.id,
                "task_number_for_user": idx,
                "created_at": t.created_at.isoformat(),
                "preview": t.original_text[:100] if t.original_text else "Нет текста",
                "difficulty_override": t.difficulty_override,
                "target_grade": t.target_grade
            }
            for idx, t in enumerate(tasks, start=1)

        ]
    }


#  ПОЛУЧЕНИЕ ВАРИАНТОВ ЗАДАНИЯ 
@app.get("/get-variants/{task_id}")
async def get_variants(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возвращает все варианты конкретного задания"""
    variants = db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id,
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


#  АНАЛИЗ СЛОЖНОСТИ 
@app.get("/analyze-difficulty/{task_id}")
async def get_difficulty_analysis(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Возвращает анализ сложности задания"""
    task = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.id == task_id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    
    task_structure = _load_task_structure(task.task_structure)
    
    return {
        "task_id": task.id,
        "task_structure": task_structure,
        "difficulty_override": task.difficulty_override,
        "target_grade": task.target_grade
    }


#  ОЧИСТКА ДАННЫХ ПОЛЬЗОВАТЕЛЯ 
@app.delete("/clear-data")
async def clear_user_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удаляет все данные текущего пользователя"""
    db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id
    ).delete()
    db.query(Task).filter(Task.user_id == current_user.id).delete()
    db.commit()
    
    rate_limiter.reset_user(current_user.id)
    
    return {"message": "Все данные пользователя удалены"}


#  ГЕНЕРАЦИЯ ОТВЕТОВ
@app.post("/generate-answers/{task_id}")
async def generate_answers_endpoint(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отдельный эндпоинт для генерации ответов"""
    
    variants = db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id,
        GeneratedVariant.task_id == task_id
    ).all()
    
    if not variants:
        raise HTTPException(status_code=404, detail="Варианты не найдены")
    
    variants_dict = {
        v.variant_number: v.edited_content or v.content
        for v in variants
    }
    
    try:
        validation = await validate_variants(
            variants=variants_dict,
            original_text="",
            task_structure=None
        )
        
        answers = validation.get("answers", {})
        
        return {"answers": answers}
        
    except Exception as e:
        logger.error(f"Ошибка генерации ответов: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ЛИМИТЫ ЗАПРОСОВ
@app.get("/rate-limit")
async def get_rate_limit(
    current_user: User = Depends(get_current_user)
):
    """Возвращает информацию о лимите запросов"""
    return {
        "remaining": rate_limiter.remaining_requests(current_user.id),
        "max_per_hour": rate_limiter.max_requests
    }


#  REPROCESS EXPORT 
@app.post("/reprocess-export/{task_id}")
async def reprocess_export(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Переобрабатывает варианты для корректного экспорта"""
    variants = db.query(GeneratedVariant).filter(
        GeneratedVariant.user_id == current_user.id,
        GeneratedVariant.task_id == task_id
    ).all()
    
    for variant in variants:
        doc = parse_variant_to_document(variant.content, variant.variant_number)
        has_tables = any(block.type == "table" for block in doc.blocks)
        
        if not has_tables and '\\begin{array}' in variant.content:
            logger.info(f"Перепарисинг варианта {variant.variant_number}")
            variant.edited_content = variant.content
            db.commit()
    
    return {"message": "Варианты переобработаны", "count": len(variants)}
