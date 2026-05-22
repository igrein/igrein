# TaskForge AI
Генератор вариантов заданий для учителей на базе GigaChat.
## Кому нужен этот сервис
- Учителям, которые тратят много времени на подготовку вариантов контрольных
- Учителям для пересдач (нужен дополнительный вариант)
- Учителям для зачётов (каждому ученику — свой вариант)
## Возможности
- Загрузка эталонного задания (текст, PDF, DOCX, изображение)
- Генерация 1–10 вариантов с сохранением сложности
- Настройка типов вариаций (числа, порядок, синонимы, контекст)
- Выбор уровня сложности (проще / так же / сложнее)
- Редактирование и перегенерация любого варианта
- Экспорт в PDF и DOCX с ответами для учителя
- Библиотека заданий и история
- Ограничение запросов (30 в час на пользователя)
## Что можно менять
- Числовые данные
- Порядок условий
- Синонимы
- Контекст задачи
## Что остаётся неизменным
- Количество шагов решения
- Дидактическая цель
  
## Технологии
- Backend: Python 3.12, FastAPI, SQLAlchemy, SQLite
- Frontend: HTML, CSS, JavaScript
- LLM: GigaChat API
- Парсинг: PyPDF2, python-docx, pytesseract (OCR)
- Экспорт: reportlab (PDF), python-docx (DOCX)

## Установка и запуск
### 1. Установите Tesseract (для OCR)
**Linux / WSL:**
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-rus

**Windows:** Скачайте Tesseract с https://github.com/UB-Mannheim/tesseract/wiki

### 2. Запустите бекенд
cd taskforge_backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

### 3. Запустите фронтенд (в новом терминале)
cd taskforge_frontend
python -m http.server 3000

### 4. Откройте в браузере
http://localhost:3000

## Настройка GigaChat (опционально)
Создайте файл .env в папке taskforge_backend:
GIGACHAT_CREDENTIALS=ваш_ключ
Без ключа сервер работает в мок-режиме.

## Автор
Киракосян Екатерина

