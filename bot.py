import os

from dotenv import load_dotenv
load_dotenv()

import asyncpg
import httpx
import json
import base64
import uuid
import re
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

#НОВОЕ
import logging
import sys
from datetime import datetime

# Используем переменные окружения
TOKEN = os.getenv('TELEGRAM_TOKEN')
GIGACHAT_API_KEY = os.getenv('GIGACHAT_API_KEY')

# Простой Flask для health check
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Hedgehog Bot is running! 🦔"

@flask_app.route('/health')
def health():
    return "OK"

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# Запускаем Flask только если это главный файл
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

# Состояния для анкеты
ASK_PET_NAME, ASK_BREED, ASK_AGE, ASK_WEIGHT, CONFIRM_PROFILE = range(5)
EDIT_CHOICE, EDIT_FIELD, EDIT_BREED,PROFILE_MANAGEMENT = range(5, 9)
PROFILE_LIST, PROFILE_DETAIL, DELETE_CONFIRM = range(9, 12)

#Породы
BREED_MAPPING = {
    "breed_african": "Африканский карликовый",
    "breed_long_eared": "Ушастый", 
    "breed_european": "Европейский",
    "breed_other": "Другая порода",
    "breed_unknown": "Порода неизвестна",
    "breed_east_european": "Восточноевропейский",
    "breed_south_white": "Южный белобрюхий",
    "breed_amur": "Амурский",
    "breed_indian": "Индийский",
    "breed_far_east": "Дальневосточный",
    "breed_somali": "Сомалийский",
    "breed_white_belly": "Белобрюхий",
    "breed_south_african": "Южноафриканский",
    "breed_north_african": "Североафриканский"
}

# Описания пород для подсказок
breed_descriptions = {
    "Африканский карликовый": "• Самый популярный домашний ёж\n• Размер: 15-20 см\n• Вес: 300-500 г\n• Окрас: разный",
    "Ушастый": "• Большие уши\n• Размер: 20-25 см\n• Вес: 400-600 г\n• Любит тепло",
    "Европейский": "• Крупный размер\n• Размер: 25-30 см\n• Вес: 600-1000 г\n• Реже встречается в домах",
    "Другая порода": "Если ваша порода не в списке"
}

# Стандарты пород
BREED_STANDARDS = {
    "Африканский карликовый": {
        "newborn_min": 8,
        "newborn_max": 20,
        "teen_min": 150,
        "teen_max": 300,
        "adult_min": 350,
        "adult_max": 600,
        "max_weight": 700,
        "teen_age_range": (2, 4),
        "adult_age": 6,
        "obesity_warning": 700,
        "life_expectancy": "3-5 лет (в неволе до 7)"
    },
    "Европейский": {
        "newborn_min": 10,
        "newborn_max": 25,
        "teen_min": 250,
        "teen_max": 500,
        "adult_min": 800,
        "adult_max": 1200,
        "max_weight": 1200,
        "teen_age_range": (2, 4),
        "adult_age": 6,
        "winter_min": 500,
        "life_expectancy": "4-7 лет (в неволе до 10)"
    },
    "Ушастый": {
        "newborn_min": 6,
        "newborn_max": 12,
        "teen_min": 150,
        "teen_max": 250,
        "adult_min": 200,
        "adult_max": 500,
        "max_weight": 600,
        "teen_age_range": (2, 4),
        "adult_age": 6,
        "obesity_warning": 500,
        "life_expectancy": "6-8 лет"
    },
    "Восточноевропейский": {
        "newborn_min": 10,
        "newborn_max": 25,
        "teen_min": 250,
        "teen_max": 500,
        "adult_min": 800,
        "adult_max": 1200,
        "max_weight": 1200,
        "teen_age_range": (2, 4),
        "adult_age": 6,
        "life_expectancy": "4-7 лет"
    },
    "Южный белобрюхий": {
        "newborn_min": 8,
        "newborn_max": 20,
        "teen_min": 150,
        "teen_max": 300,
        "adult_min": 350,
        "adult_max": 600,
        "max_weight": 700,
        "teen_age_range": (2, 4),
        "adult_age": 6,
        "life_expectancy": "3-5 лет"
    }
}

# Для пород без специфичных стандартов используем общие
DEFAULT_STANDARDS = {
    "newborn_min": 8,
    "newborn_max": 25,
    "teen_min": 150,
    "teen_max": 400,
    "adult_min": 300,
    "adult_max": 800,
    "max_weight": 900,
    "teen_age_range": (2, 4),
    "adult_age": 6,
    "life_expectancy": "3-6 лет"
}

PROFILES_PER_PAGE = 5

# Данные для подключения к PostgreSQL
DB_CONFIG = {
    'user': 'gen_user',
    'password': 'JZ6vG{7w5vds#%',
    'database': 'default_db',
    'host': '02c7c32ab3df2662b02f9acb.twc1.net',
    'port': 5432,
    'ssl': 'require'
}

# Клавиатура главного меню
MAIN_MENU_KEYBOARD = [
    ["🦔 Задать вопрос про моего ежика", "📋 Анкеты моих ежиков"],
    ["❓Задать вопрос без анкеты", "➕ Добавить ежика"],
    ["💡 Что я умею"]
]

MAIN_MENU_MARKUP = ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True)

# Клавиатура для возврата
BACK_TO_MENU_KEYBOARD = [["⬅️ Вернуться в главное меню"]]
BACK_TO_MENU_MARKUP = ReplyKeyboardMarkup(BACK_TO_MENU_KEYBOARD, resize_keyboard=True, one_time_keyboard=True)

# Клавиатура для продолжения после ответа
CONTINUE_QUESTION_KEYBOARD = [
    ["❓ Задать еще вопрос", "⬅️ Вернуться в главное меню"]
]
CONTINUE_QUESTION_MARKUP = ReplyKeyboardMarkup(CONTINUE_QUESTION_KEYBOARD, resize_keyboard=True, one_time_keyboard=True)

#НОВОЕ
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('HedgehogBot')

# Дополнительная функция для логирования ошибок БД
async def log_db_error(user_id, operation, error):
    logger.error(f"DB Error - User: {user_id}, Operation: {operation}, Error: {error}")

# Дополнительная функция для логирования успешных операций
async def log_success(user_id, operation, details=""):
    logger.info(f"Success - User: {user_id}, Operation: {operation}, Details: {details}")


#NEW
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start. Показывает главное меню."""
    user = update.effective_user
    logger.info(f"Start command received from user: {user.id}, {user.username}, {user.first_name}")
    
    try:
        # Пытаемся сохранить пользователя, но не блокируем весь процесс при ошибке
        save_success = await save_user_to_db(user.id, user.username, user.first_name)
        
        if not save_success:
            logger.warning(f"Failed to save user {user.id} to DB, but continuing with start flow")
        
        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "Добро пожаловать в HedgeAiCare — умную заботу о колючем друге 🦔\n\n"
            "🔎 Я могу:\n"
            "• Ответить на вопросы о содержании, питании и гигиене ежей\n"
            "• Учитывать особенности именно вашего питомца, если заполните анкету\n\n"
            "⚠️ Важно: мои советы носят справочный характер и не заменяют консультацию ветеринара-ратолога.\n\n"
            "Выберите, с чего хотите начать заботу о вашем ежике, в меню ниже ⬇️"
        )
        
        # Очистка контекста при новом старте
        context.user_data.clear()
        
        await update.message.reply_text(welcome_text, reply_markup=MAIN_MENU_MARKUP)
        logger.info(f"Start message successfully sent to user {user.id}")
        
    except Exception as e:
        logger.error(f"Critical error in start handler for user {user.id}: {str(e)}")
        # Даже при ошибке пытаемся отправить сообщение
        try:
            emergency_text = (
                f"👋 Привет, {user.first_name}!\n\n"
                "Добро пожаловать в HedgeAiCare — умную заботу о колючем друге 🦔\n\n"
                "Произошла временная техническая ошибка, но вы можете продолжить работу.\n\n"
                "Выберите действие в меню ниже ⬇️"
            )
            await update.message.reply_text(emergency_text, reply_markup=MAIN_MENU_MARKUP)
        except Exception as inner_e:
            logger.critical(f"Complete failure for user {user.id}: {str(inner_e)}")



async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Центральный обработчик для кнопок главного меню."""
    user_choice = update.message.text

    if user_choice == "📋 Анкеты моих ежиков":
        await go_to_my_profiles(update, context)

    elif user_choice == "➕ Добавить ежика":
        for key in ['pet_name', 'breed', 'age', 'weight', 'editing_profile_id', 'editing_field']:
                if key in context.user_data:
                    del context.user_data[key]
        await start_profile_form(update, context)
  
    elif user_choice == "❓ Задать еще вопрос":
        if 'waiting_for_general_question' in context.user_data:
            del context.user_data['waiting_for_general_question']
        await ask_general_question(update, context)
        return
    
    elif user_choice == "❓Задать вопрос без анкеты":
        await ask_general_question(update, context)

    elif user_choice == "🦔 Задать вопрос про моего ежика":
        await ask_about_my_hedgehog(update, context)

    elif user_choice == "💡 Что я умею":
        await show_help(update, context)

    elif user_choice == "⬅️ Вернуться в главное меню":
        if 'in_general_question_mode' in context.user_data:
            del context.user_data['in_general_question_mode']
        if 'waiting_for_general_question' in context.user_data:
            del context.user_data['waiting_for_general_question']
        
        await update.message.reply_text("Главное меню:", reply_markup=MAIN_MENU_MARKUP)
        context.user_data.clear()

    else:
        await update.message.reply_text("Пожалуйста, выберите действие из меню ниже:", reply_markup=MAIN_MENU_MARKUP)


#КНОПКА Что я умею
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка '💡 Что я умею'."""
    help_text = (

        "Я — HedgeAiCare бот 🦔. Забочусь о ваших ежиках и помогаю получать полезные советы.\n\n"
        "Вот что я умею:\n"
        "• 📋 Анкеты моих ежиков — просмотр и управление анкетами ваших ежей\n"
        "• ➕ Добавить ежика — создать новую анкету для вашего питомца\n"
        "• ❓Задать вопрос без анкеты — задать вопрос о ежах в целом\n"
        "• 🦔 Задать вопрос про моего ежика — задать вопрос с учетом данных из анкеты\n\n"
        "⚠️ Важно: информация носит справочный характер. При срочных или критических ситуациях обязательно обращайтесь к ветеринару-ратологу.\n\n"
        "Чтобы начать общение заново, просто напишите /start\n\n"
        "Выберите нужное действие в меню ниже 👇"
    )

    await update.message.reply_text(help_text, reply_markup=MAIN_MENU_MARKUP)

#КНОПКА Добавить ежика и функции к ее логике
async def start_profile_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для кнопки '➕ Добавить ежика'. Начинает процесс создания анкеты."""
    # Очищаем контекст от возможных старых данных
    context.user_data.clear()
            
    await update.message.reply_text(
        """Давайте заполним анкету вашего ежика! 🦔
Если вдруг захотите остановиться — просто напишите /cancel 
Как зовут ежика??""",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_PET_NAME

async def ask_pet_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем кличку с проверкой уникальности"""
    pet_name = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Проверяем уникальность клички
    exclude_profile_id = context.user_data.get('editing_profile_id')
    is_unique = await is_pet_name_unique(user_id, pet_name, exclude_profile_id)
    
    if not is_unique:
        # Получаем список существующих ежиков для подсказки
        conn = await get_db_connection()
        try:
            profiles = await conn.fetch(
                "SELECT pet_name, profile_id FROM HedgehogProfiles WHERE user_id = $1 ORDER BY pet_name",
                user_id
            )
            
            existing_names = [profile['pet_name'] for profile in profiles]
            existing_list = "\n".join([f"• {name}" for name in existing_names])
            
            message_text = (
                f"❌ Ежик с кличкой '{pet_name}' уже есть в ваших анкетах!\n\n"
                f"📋 Ваши текущие ежики:\n{existing_list}\n\n"
                "Пожалуйста, придумайте уникальную кличку для вашего нового ежика 🦔\n"
                "Если вы хотели изменить данные уже существующего питомца, это можно сделать в разделе «Анкеты моих ежиков».\n\n"
                "Чтобы прервать создание анкеты, просто напишите /cancel — и мы вернёмся в главное меню."
            )
            
            await update.message.reply_text(message_text)
            return ASK_PET_NAME
            
        finally:
            await conn.close()
    
    context.user_data['pet_name'] = pet_name
    
    breed_text = """
🐾 **Давайте выберем породу вашего ежа:**

• **Африканский карликовый** - самый популярный домашний ёж
• **Ушастый** - отличается большими ушами  
• **Европейский** - крупный лесной ёжик
• **Другая порода** - если вашей породы нет в списке, посмотрите дополнительный
• **Не знаю породу** - покажем примеры фотографий
"""
    
    await update.message.reply_text(
        breed_text,
        reply_markup=get_breed_keyboard(),
        parse_mode='Markdown'
    )
    return ASK_BREED

async def is_pet_name_unique(user_id: int, pet_name: str, exclude_profile_id: int = None) -> bool:
    """Проверяет, уникальна ли кличка для данного пользователя"""
    conn = await get_db_connection()
    try:
        if exclude_profile_id:
            # Для редактирования: проверяем уникальность, исключая текущую анкету
            existing = await conn.fetchrow(
                """SELECT profile_id FROM HedgehogProfiles 
                WHERE user_id = $1 AND LOWER(pet_name) = LOWER($2) AND profile_id != $3""",
                user_id, pet_name, exclude_profile_id
            )
        else:
            # Для создания новой анкеты
            existing = await conn.fetchrow(
                """SELECT profile_id FROM HedgehogProfiles 
                WHERE user_id = $1 AND LOWER(pet_name) = LOWER($2)""",
                user_id, pet_name
            )
        return existing is None
    finally:
        await conn.close()

async def handle_breed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем выбор породы через инлайн-кнопки"""
    query = update.callback_query
    await query.answer()
    
    #
    callback_data = query.data
    
    if callback_data == "show_breed_examples":
        await send_breed_examples(query.message)
        await query.message.reply_text(
            "🐾 Выберите породу вашего ежика:",
            reply_markup=get_breed_keyboard()
        )
        return ASK_BREED 
        
    elif callback_data in BREED_MAPPING:
        selected_breed = BREED_MAPPING[callback_data]
        
        if callback_data == "breed_other":
            other_breeds_keyboard = [
                [InlineKeyboardButton("Восточноевропейский", callback_data="breed_east_european")],
                [InlineKeyboardButton("Южный белобрюхий", callback_data="breed_south_white")],
                [InlineKeyboardButton("Амурский", callback_data="breed_amur")],
                [InlineKeyboardButton("Индийский", callback_data="breed_indian")],
                [InlineKeyboardButton("Дальневосточный", callback_data="breed_far_east")],
                [InlineKeyboardButton("Сомалийский", callback_data="breed_somali")],
                [InlineKeyboardButton("Белобрюхий", callback_data="breed_white_belly")],
                [InlineKeyboardButton("Южноафриканский", callback_data="breed_south_african")],
                [InlineKeyboardButton("Североафриканский", callback_data="breed_north_african")],
                [InlineKeyboardButton("➡️ Продолжить без указания породы", callback_data="breed_unknown")]
            ]
            
            await query.edit_message_text(
                "🐾 Выберите породу из дополнительного списка:",
                reply_markup=InlineKeyboardMarkup(other_breeds_keyboard)
            )
            return ASK_BREED 
            
        else:
            context.user_data['breed'] = selected_breed
            await query.edit_message_text(
                f"✅ Выбрана порода: {selected_breed}",
                reply_markup=None
            )
            
            if context.user_data.get('editing_field') == 'breed':
                await query.message.reply_text(
                    "Хотите изменить что-то еще?",
                    reply_markup=get_edit_keyboard() 
                )
                return EDIT_CHOICE
            else:
                await query.message.reply_text("Теперь укажите возраст ежика в месяцах:")
                return ASK_AGE
    
    elif callback_data in ["breed_east_european", "breed_south_white", "breed_amur", 
                          "breed_indian", "breed_far_east", "breed_somali",
                          "breed_white_belly", "breed_south_african", "breed_north_african"]:
        selected_breed = BREED_MAPPING[callback_data]
        context.user_data['breed'] = selected_breed
        await query.edit_message_text(
            f"✅ Выбрана порода: {selected_breed}",
            reply_markup=None
        )
        
        if context.user_data.get('editing_field') == 'breed':
            await query.message.reply_text(
                "Хотите изменить что-то еще?",
                reply_markup=get_edit_keyboard()
            )
            return EDIT_CHOICE
        else:
            await query.message.reply_text("Теперь укажите возраст в месяцах:")
            return ASK_AGE
    
    return ASK_BREED

async def send_breed_examples(message):
    """Отправляем примеры пород с фото"""
    breeds_info = {
        "Африканский карликовый": {
            "description": "• Самый популярный домашний ёж\n• Размер: 15-20 см\n• Вес: 300-500 г",
            "photo_url": "https://animal.by/wp-content/uploads/2017/09/ezh5.jpg"
        },
        "Ушастый": {
            "description": "• Большие уши\n• Размер: 20-25 см\n• Вес: 400-600 г", 
            "photo_url": "https://cdn.puzzlegarage.com/img/puzzle/1e/12798_preview.v1.jpg"
        },
        "Европейский": {
            "description": "• Крупный размер\n• Размер: 25-30 см\n• Вес: 600-1000 г",
            "photo_url": "https://avatars.dzeninfra.ru/get-zen_doc/3531468/pub_5f26858c5536b565331b99c6_5f2a5cf92a705c1d686b4994/scale_1200"
        }
    }
    
    for breed, info in breeds_info.items():
        try:
            await message.reply_photo(
                photo=info['photo_url'],
                caption=f"🐾 **{breed}**\n{info['description']}",
                parse_mode='Markdown'
            )
        except Exception as e:
            # Если не удалось отправить фото, отправляем только текст
            await message.reply_text(
                f"🐾 **{breed}**\n{info['description']}",
                parse_mode='Markdown'
            )

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем возраст"""
    try:
        age = int(update.message.text)
        if age < 0 or age > 144:  
            await update.message.reply_text("❌ Возраст должен быть от 0 до 144 месяцев. Проверьте и введите снова:")
            return ASK_AGE
            
        context.user_data['age'] = age
        await update.message.reply_text("Отлично! Теперь укажите вес в граммах:")
        return ASK_WEIGHT
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число для возраста:")
        return ASK_AGE

async def ask_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем вес"""
    try:
        weight = int(update.message.text)
        if weight < 5 or weight > 5000:
            await update.message.reply_text("❌ Вес должен быть от 5 до 2500 грамм. Проверьте и введите снова:")
            return ASK_WEIGHT
            
        context.user_data['weight'] = weight
        
        summary = f"""
📋 Проверьте данные:

• Кличка: {context.user_data['pet_name']}
• Порода: {context.user_data['breed']}
• Возраст: {context.user_data['age']} месяцев
• Вес: {context.user_data['weight']} грамм

Всё верно?
"""
        keyboard = [["✅ Да", "✏️ Исправить", "↩️ Заполнить заново"],
                    ["⬅️ Вернуться в главное меню"]
                    ]
        await update.message.reply_text(
            summary,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return CONFIRM_PROFILE
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число для веса:")
        return ASK_WEIGHT

async def confirm_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняет или обновляет анкету"""
    if update.message.text == "⬅️ Вернуться в главное меню":
            context.user_data.clear()
            await update.message.reply_text(
                "Главное меню:",
                reply_markup=MAIN_MENU_MARKUP
            )
            return ConversationHandler.END

    elif update.message.text == "✅ Да":
        user_id = update.message.from_user.id
        pet_name = context.user_data['pet_name']
        breed = context.user_data['breed']
        age = context.user_data['age']
        weight = context.user_data['weight']
                
        conn = await get_db_connection()
        try:
            if 'editing_profile_id' in context.user_data:
                # Редактирование существующей анкеты
                profile_id = context.user_data['editing_profile_id']
                await conn.execute(
                    """UPDATE HedgehogProfiles 
                    SET pet_name = $1, hedgehog_breed = $2, hedgehog_age = $3, hedgehog_weight = $4
                    WHERE profile_id = $5""",
                    pet_name, breed, age, weight, profile_id
                )
                message = "✅ Анкета обновлена!\nТеперь обновлённые данные можно посмотреть в разделе «Анкеты моих ежиков» 🦔"
                del context.user_data['editing_profile_id']
            else:
                # Создание новой анкеты
                await conn.execute(
                    """INSERT INTO HedgehogProfiles 
                    (user_id, pet_name, hedgehog_breed, hedgehog_age, hedgehog_weight) 
                    VALUES ($1, $2, $3, $4, $5)""",
                    user_id, pet_name, breed, age, weight
                )
                message = "✅ Анкета сохранена!\n Вы можете посмотреть ее в разделе «Анкеты моих ежиков»"
            
            await update.message.reply_text(message, reply_markup=MAIN_MENU_MARKUP)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка сохранения: {e}")
        finally:
            await conn.close()
            
   
    elif update.message.text == "✏️ Исправить":
        await update.message.reply_text(
            "Какое поле хотите исправить?",
            reply_markup=ReplyKeyboardRemove() 
        )
        await update.message.reply_text(
            "Выберите поле:",
            reply_markup=get_edit_keyboard()
        )
        return EDIT_CHOICE
        
    else:
        await update.message.reply_text(
            "Хорошо, начнем заново! Как зовут вашего питомца?",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_PET_NAME
    
    return ConversationHandler.END

async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем выбор поля для редактирования через инлайн-кнопки"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "edit_pet_name":
        await query.message.reply_text("Введите новую кличку:", reply_markup=ReplyKeyboardRemove())
        context.user_data['editing_field'] = 'pet_name'
        return EDIT_FIELD
        
    elif callback_data == "edit_breed":
        context.user_data['editing_field'] = 'breed'
        await query.message.reply_text(
            "Выберите новую породу:",
            reply_markup=get_breed_keyboard()
        )
        return EDIT_BREED
        
    elif callback_data == "edit_age":
        await query.message.reply_text("Введите новый возраст:", reply_markup=ReplyKeyboardRemove())
        context.user_data['editing_field'] = 'age'
        return EDIT_FIELD
        
    elif callback_data == "edit_weight":
        await query.message.reply_text("Введите новый вес:", reply_markup=ReplyKeyboardRemove())
        context.user_data['editing_field'] = 'weight'
        return EDIT_FIELD
        
    elif callback_data == "edit_done":
        required_fields = ['pet_name', 'breed', 'age', 'weight']
        for field in required_fields:
            if field not in context.user_data:
                await query.message.reply_text(f"❌ Отсутствует поле {field}. Пожалуйста, заполните все поля.")
                return EDIT_CHOICE

    summary = f"""
📋 Проверьте обновленные данные:

• Кличка: {context.user_data['pet_name']}
• Порода: {context.user_data['breed']}
• Возраст: {context.user_data['age']} месяцев
• Вес: {context.user_data['weight']} грамм

Всё верно?
"""

    await query.edit_message_text("✅ Редактирование завершено.")

    keyboard = [["✅ Да", "✏️ Исправить", "↩️ Заполнить заново"],
                ["⬅️ Вернуться в главное меню"]]
    await query.message.reply_text(
        summary,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return CONFIRM_PROFILE

def get_breed_keyboard():
    """Инлайн-кнопки для выбора породы с добавлением кнопки продолжения без указания"""
    keyboard = [
        [InlineKeyboardButton("🐾 Африканский карликовый", callback_data="breed_african")],
        [InlineKeyboardButton("👂 Ушастый", callback_data="breed_long_eared")],
        [InlineKeyboardButton("🌲 Европейский", callback_data="breed_european")],
        [InlineKeyboardButton("❓ Другая порода", callback_data="breed_other")],
        [InlineKeyboardButton("📸 Показать фото пород", callback_data="show_breed_examples")],
        [InlineKeyboardButton("➡️ Продолжить без указания породы", callback_data="breed_unknown")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_edit_keyboard():
    """Инлайн-кнопки для выбора поля редактирования"""
    keyboard = [
        [InlineKeyboardButton("✏️ Кличка", callback_data="edit_pet_name")],
        [InlineKeyboardButton("✏️ Порода", callback_data="edit_breed")],
        [InlineKeyboardButton("✏️ Возраст", callback_data="edit_age")],
        [InlineKeyboardButton("✏️ Вес", callback_data="edit_weight")],
        [InlineKeyboardButton("✅ Всё верно", callback_data="edit_done")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handle_field_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает редактирование конкретного поля"""
    field = context.user_data['editing_field']
    new_value = update.message.text.strip()
    

    if field == 'pet_name':
        user_id = update.message.from_user.id
        exclude_profile_id = context.user_data.get('editing_profile_id')
        is_unique = await is_pet_name_unique(user_id, new_value, exclude_profile_id)
        
        if not is_unique:
            await update.message.reply_text(
                f"❌ Ежик с кличкой '{new_value}' уже есть в ваших анкетах!\n"
                "Пожалуйста, придумайте для питомца другое имя, чтобы не запутаться 🦔:"
            )
            return EDIT_FIELD
    
    # Валидация числовых полей
    if field in ['age', 'weight']:
        try:
            new_value = int(new_value)
            if field == 'weight' and (new_value < 5 or new_value > 2500): 
                await update.message.reply_text("❌ Неверный вес! Введите вес от 5 до 2500 грамм:")
                return EDIT_FIELD
            elif field == 'age' and (new_value < 0 or new_value > 144):  
                await update.message.reply_text("❌ Неверный возраст! Введите возраст от 0 до 144 месяцев:")
                return EDIT_FIELD
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите число:")
            return EDIT_FIELD
    
    context.user_data[field] = new_value
    
    await update.message.reply_text(
        f"✅ {field.replace('_', ' ').title()} обновлено!",
        reply_markup=ReplyKeyboardRemove()
    )

    await update.message.reply_text(
        "Хотите изменить что-то еще?",
        reply_markup=get_edit_keyboard()
    )
    return EDIT_CHOICE

async def cancel_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена заполнения анкеты"""
    await update.message.reply_text(
        "Заполнение анкеты отменено.",
        reply_markup=MAIN_MENU_MARKUP 
    )
    return ConversationHandler.END


#БАЗА ДАННЫХ

#НОВОЕ
async def save_user_to_db(user_id, username, first_name):
    """Сохраняет пользователя в таблицу Users с обработкой ошибок"""
    logger.info(f"Attempting to save user to DB: {user_id}, {username}, {first_name}")
    
    max_retries = 3
    retry_delay = 2  # секунды
    
    for attempt in range(max_retries):
        try:
            conn = await get_db_connection()
            try:
                await conn.execute(
                    "INSERT INTO Users (user_id, user_name, first_name) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING",
                    user_id, username, first_name
                )
                await log_success(user_id, "save_user", f"Attempt {attempt + 1}")
                logger.info(f"User {user_id} successfully saved to database")
                return True
                
            except Exception as e:
                await log_db_error(user_id, "save_user", f"Attempt {attempt + 1}: {str(e)}")
                logger.error(f"Database error while saving user {user_id}: {str(e)}")
                raise
                
            finally:
                await conn.close()
                
        except asyncpg.exceptions.ConnectionDoesNotExistError:
            logger.warning(f"Connection error attempt {attempt + 1} for user {user_id}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to save user {user_id} after {max_retries} attempts")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error saving user {user_id}: {str(e)}")
            return False
    
    return False

async def get_db_connection():
    """Создает подключение к базе данных с таймаутом и логированием"""
    logger.info("Attempting to create database connection")
    
    try:
        # Добавляем таймаут подключения
        conn = await asyncpg.connect(
            **DB_CONFIG,
            timeout=30.0  # 30 секунд таймаут
        )
        logger.info("Database connection established successfully")
        return conn
        
    except Exception as e:
        logger.error(f"Failed to establish database connection: {str(e)}")
        raise

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    # Логируем детали update
    if update and update.effective_user:
        logger.error(f"Error for user: {update.effective_user.id}")
    
    # Можно отправить сообщение администратору или пользователю
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 Произошла техническая ошибка. Пожалуйста, попробуйте еще раз."
            )
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")

async def check_db_connection():
    """Проверяет доступность базы данных"""
    try:
        conn = await get_db_connection()
        await conn.close()
        logger.info("Database connection check: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Database connection check: FAILED - {e}")
        return False

# Запускайте эту проверку периодически или при старте


#КНОПКА Анкеты ежей и функции к ее логике
async def go_to_my_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список анкет пользователя с инлайн-кнопками или предлагает создать новую"""
    user_id = update.effective_user.id
    
    try:
        conn = await get_db_connection()
        profiles = await conn.fetch(
            "SELECT * FROM HedgehogProfiles WHERE user_id = $1 ORDER BY pet_name",
            user_id
        )
        
        if not profiles:
            keyboard = [
                [InlineKeyboardButton("➕ Добавить ежика", callback_data="trigger_add_via_menu")],
            ]
            reply_text = "У вас пока нет анкет 🦔. Хотите добавить первого ежика?"
            
            if hasattr(update, 'message'):
                await update.message.reply_text(reply_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.edit_message_text(reply_text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        context.user_data['user_profiles'] = [dict(profile) for profile in profiles]
        context.user_data['current_page'] = 0
        
        await show_profiles_page(update, context, page=0)
        
    except Exception as e:
        error_text = f"❌ Ошибка при загрузке анкет: {e}"
        if hasattr(update, 'message'):
            await update.message.reply_text(error_text)
        else:
            await update.edit_message_text(error_text)
    finally:
        if conn:
            await conn.close()

async def show_profiles_page(update, context, page=0):
    """Показывает страницу со списком анкет"""
    profiles = context.user_data['user_profiles']
    total_pages = max(1, (len(profiles) + PROFILES_PER_PAGE - 1) // PROFILES_PER_PAGE)
    
    start_idx = page * PROFILES_PER_PAGE
    end_idx = min(start_idx + PROFILES_PER_PAGE, len(profiles))
    page_profiles = profiles[start_idx:end_idx]
    
    keyboard = []
    for profile in page_profiles:
        keyboard.append([InlineKeyboardButton(
            f"🦔 {profile['pet_name']} ({profile['hedgehog_breed']})", 
            callback_data=f"view_profile_{profile['profile_id']}"
        )])
    
    if total_pages > 1:
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"profiles_page_{page-1}"))
        pagination_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"profiles_page_{page+1}"))
        
        keyboard.append(pagination_buttons)
    
    keyboard.append([InlineKeyboardButton("➕ Добавить ежика", callback_data="trigger_add_via_menu")])

    
    text = f"📋 Ваши ежики:\n\n"
    for i, profile in enumerate(page_profiles, start=1):
        text += f"{i}. {profile['pet_name']} - {profile['hedgehog_breed']}\n"

    text += f"\n👇 Выберите анкету — можно посмотреть, что-то исправить или задать вопрос"

    if total_pages > 1:
        text += f"\n\nСтраница {page+1}/{total_pages}"

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif hasattr(update, 'edit_message_text'):
        await update.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

def get_profile_management_keyboard(profile_id):
    """Инлайн-кнопки для управления анкетой"""
    keyboard = [
        [InlineKeyboardButton("❓ Задать вопрос", callback_data=f"ask_question_{profile_id}")],
        [InlineKeyboardButton("🌿 Сверить с породной нормой", callback_data=f"check_weight_{profile_id}")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_profile_{profile_id}")],
        [InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_profile_{profile_id}")],
        [InlineKeyboardButton("📋 Назад к списку", callback_data="back_to_profiles")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_profile_detail(query, context, profile):
    """Показывает детали анкеты с инлайн-кнопками управления"""
    profile_text = f"""
🦔 {profile['pet_name']}

• Кличка: {profile['pet_name']}
• Порода: {profile['hedgehog_breed']}
• Возраст: {profile['hedgehog_age']} месяцев
• Вес: {profile['hedgehog_weight']} грамм
"""
    await query.edit_message_text(
        profile_text, 
        reply_markup=get_profile_management_keyboard(profile['profile_id'])
    )

async def handle_profile_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор конкретной анкеты"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("view_profile_"):
        profile_id = int(query.data.split("_")[2])
        
        try:
            conn = await get_db_connection()
            profile = await conn.fetchrow(
                "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            
            if profile:
                await show_profile_detail(query, context, dict(profile))
            else:
                await query.edit_message_text("❌ Анкета не найдена")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при загрузке анкеты: {e}")
        finally:
            if conn:
                await conn.close()

async def handle_profile_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает действия с анкетой"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("ask_question_"):
        profile_id = int(callback_data.split("_")[2])
        context.user_data['selected_profile_id'] = profile_id
        
        # Получаем данные анкеты для контекста
        conn = None
        try:
            conn = await get_db_connection()
            profile = await conn.fetchrow(
                "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            
            if profile:
                context.user_data['current_profile'] = dict(profile)
                await query.edit_message_text(
                    "Напишите ваш вопрос о ежике:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Отмена", callback_data="back_to_profiles")]])
                )
                context.user_data['waiting_for_profile_question'] = True
            else:
                await query.edit_message_text("❌ Анкета не найдена")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при загрузке анкеты: {e}")
        finally:
            if conn:
                await conn.close()

    elif callback_data.startswith("check_weight_"):
        await handle_weight_check(update, context)
        
    elif callback_data.startswith("edit_profile_"):
        profile_id = int(callback_data.split("_")[2])
        
        conn = None
        try:
            conn = await get_db_connection()
            profile = await conn.fetchrow(
                "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            
            if profile:
                profile_dict = dict(profile)
                # Сохраняем данные анкеты в context для редактирования
                context.user_data.update({
                    'editing_profile_id': profile_id,
                    'pet_name': profile_dict['pet_name'],
                    'breed': profile_dict['hedgehog_breed'],
                    'age': profile_dict['hedgehog_age'],
                    'weight': profile_dict['hedgehog_weight']
                })
                
                # Показываем текущие данные и предлагаем редактировать
                summary = f"""
    📋 Редактирование анкеты:

    • Кличка: {profile_dict['pet_name']}
    • Порода: {profile_dict['hedgehog_breed']}
    • Возраст: {profile_dict['hedgehog_age']} месяцев
    • Вес: {profile_dict['hedgehog_weight']} грамм

    Что хотите изменить?
    """
                await query.edit_message_text(
                    summary,
                    reply_markup=get_edit_keyboard()
                )
                return EDIT_CHOICE
                
            else:
                await query.edit_message_text("❌ Анкета не найдена")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при загрузке анкеты: {e}")
        finally:
            if conn:
                await conn.close()
        
    elif callback_data.startswith("delete_profile_"):
        profile_id = int(callback_data.split("_")[2])
        await confirm_delete_profile(query, context, profile_id)

async def confirm_delete_profile(query, context, profile_id):
    """Запрашивает подтверждение удаления анкеты"""
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{profile_id}")],
        [InlineKeyboardButton("❌ Нет, отменить", callback_data=f"cancel_delete_{profile_id}")]
    ]
    
    await query.edit_message_text(
        "❓ Вы уверены, что хотите удалить эту анкету? Это действие нельзя отменить.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_delete_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает подтверждение удаления анкеты"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("confirm_delete_"):
        profile_id = int(query.data.split("_")[2])
        
        conn = None
        try:
            conn = await get_db_connection()
            await conn.execute(
                "DELETE FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            await query.edit_message_text("✅ Анкета успешно удалена!")
            
            user_id = query.from_user.id
            
            profiles = await conn.fetch(
                "SELECT * FROM HedgehogProfiles WHERE user_id = $1 ORDER BY pet_name",
                user_id
            )
            
            if not profiles:
                keyboard = [
                    [InlineKeyboardButton("➕ Добавить ежика", callback_data="trigger_add_via_menu")],
                ]
                await query.edit_message_text(
                    "У вас пока нет анкет 🦔. Хотите добавить ежа?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                context.user_data['user_profiles'] = [dict(profile) for profile in profiles]
                context.user_data['current_page'] = 0
                await show_profiles_page(query, context, page=0)
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при удалении: {e}")
        finally:
            if conn:
                await conn.close()
    elif query.data.startswith("cancel_delete_"):
        profile_id = int(query.data.split("_")[2])
        try:
            conn = await get_db_connection()
            profile = await conn.fetchrow(
                "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            if profile:
                await show_profile_detail(query, context, dict(profile))
            else:
                await query.edit_message_text("❌ Анкета не найдена")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
        finally:
            if conn:
                await conn.close()

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает навигационные команды"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("profiles_page_"):
        page = int(query.data.split("_")[2])
        context.user_data['current_page'] = page
        
        # Проверяем, есть ли данные профилей в контексте
        if 'user_profiles' not in context.user_data:
            # Если нет, загружаем заново
            user_id = query.from_user.id
            conn = None
            try:
                conn = await get_db_connection()
                profiles = await conn.fetch(
                    "SELECT * FROM HedgehogProfiles WHERE user_id = $1 ORDER BY pet_name",
                    user_id
                )
                context.user_data['user_profiles'] = [dict(profile) for profile in profiles]
            except Exception as e:
                await query.edit_message_text(f"❌ Ошибка при загрузке анкет: {e}")
                return
            finally:
                if conn:
                    await conn.close()
        
        await show_profiles_page(query, context, page)
        
    elif query.data == "back_to_profiles":
        for key in ['editing_profile_id', 'pet_name', 'breed', 'age', 'weight', 'editing_field']:
            if key in context.user_data:
                del context.user_data[key]
        
        # Загружаем профили заново при возврате
        user_id = query.from_user.id
        conn = None
        try:
            conn = await get_db_connection()
            profiles = await conn.fetch(
                "SELECT * FROM HedgehogProfiles WHERE user_id = $1 ORDER BY pet_name",
                user_id
            )
            context.user_data['user_profiles'] = [dict(profile) for profile in profiles]
            current_page = context.user_data.get('current_page', 0)
            await show_profiles_page(query, context, current_page)
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при загрузке анкет: {e}")
        finally:
            if conn:
                await conn.close()

async def handle_noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает пустые callback'и (например, кнопка с номером страницы)"""
    query = update.callback_query
    await query.answer()

async def trigger_add_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Колбэк для кнопки добавления из раздела просмотра анкет"""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.message.delete()
    except Exception as e:
        print(f"Не удалось удалить сообщение: {e}")
    
    for key in ['pet_name', 'breed', 'age', 'weight', 'editing_profile_id', 'editing_field']:
        if key in context.user_data:
            del context.user_data[key]
    
    context.user_data['starting_from_profiles'] = True
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="""Давайте заполним анкету вашего ежика! 🦔
Если вдруг захотите остановиться — просто напишите /cancel 
Как зовут ежика??""",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ASK_PET_NAME

async def handle_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовый выбор поля для редактирования"""
    choice = update.message.text.lower()
    
    if 'кличка' in choice:
        await update.message.reply_text("Введите новую кличку:", reply_markup=ReplyKeyboardRemove())
        context.user_data['editing_field'] = 'pet_name'
        return EDIT_FIELD
        
    elif 'порода' in choice:
        context.user_data['editing_field'] = 'breed'

        await update.message.reply_text("Выберите новую породу:", reply_markup=ReplyKeyboardRemove())

        await update.message.reply_text(
            "Выберите породу:",
            reply_markup=get_breed_keyboard()
        )
        return EDIT_BREED
        
    elif 'возраст' in choice:
        await update.message.reply_text("Введите новый возраст:", reply_markup=ReplyKeyboardRemove())
        context.user_data['editing_field'] = 'age'
        return EDIT_FIELD
        
    elif 'вес' in choice:
        await update.message.reply_text("Введите новый вес:", reply_markup=ReplyKeyboardRemove())
        context.user_data['editing_field'] = 'weight'
        return EDIT_FIELD
        
    else:

        await update.message.reply_text(
            "Пожалуйста, выберите поле для редактирования:",
            reply_markup=ReplyKeyboardRemove()
        )

        await update.message.reply_text(
            "Выберите поле:",
            reply_markup=get_edit_keyboard()
        )
        return EDIT_CHOICE

async def handle_profile_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки 'Задать вопрос' в меню анкеты"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("ask_question_"):
        profile_id = int(query.data.split("_")[2])
        context.user_data['selected_profile_id'] = profile_id
        
        conn = None
        try:
            conn = await get_db_connection()
            profile = await conn.fetchrow(
                "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            
            if profile:
                context.user_data['current_profile'] = dict(profile)
                context.user_data['waiting_for_profile_question'] = True
                
                cancel_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Отмена", callback_data=f"cancel_question_{profile_id}")]
                ])
                
                await query.edit_message_text(
                    "💬 Напишите ваш вопрос о ежике:",
                    reply_markup=cancel_keyboard
                )
            else:
                await query.edit_message_text("❌ Анкета не найдена")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
        finally:
            if conn:
                await conn.close()

async def handle_profile_question_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовый вопрос с данными анкеты"""
    if not context.user_data.get('waiting_for_profile_question'):
        return

    profile_id = context.user_data.get('selected_profile_id')
    if not profile_id:
        await update.message.reply_text("❌ Не удалось определить, о ком вопрос. Попробуйте снова.")
        context.user_data['waiting_for_profile_question'] = False
        return

    question = update.message.text
    context.user_data['waiting_for_profile_question'] = False

    processing_msg = await update.message.reply_text("🔍 Анализирую ваш вопрос...")

    conn = None
    try:
        conn = await get_db_connection()
        profile = await conn.fetchrow(
            "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
            profile_id
        )

        if not profile:
            await processing_msg.edit_text("❌ Анкета ежа не найдена. Возможно, она была удалена.")
            await show_continue_options(update, context)
            return

        profile_data = dict(profile)
        pet_name = profile_data.get('pet_name', 'ежике')

        await processing_msg.edit_text(f"🔍 Анализирую ваш вопрос о {pet_name}...")

    except Exception as e:
        await processing_msg.edit_text(f"❌ Ошибка при загрузке данных анкеты: {e}")
        await show_continue_options(update, context)
        return
    finally:
        if conn:
            await conn.close()

    question_type = await classify_question(question)

    if question_type == 'critical':
        critical_warning = (
            f"🚨 В вашем вопросе о {pet_name} обнаружены признаки критической ситуации!\n\n"
            "НЕМЕДЛЕННО обратитесь к ветеринару-ратологу!\n\n"
            "Я не могу давать рекомендации по критическим случаям."
        )
        await processing_msg.edit_text(critical_warning)
        await show_continue_options(update, context)
        return

    is_medical = (question_type == 'medical')
    answer = await generate_answer(question, profile_data, is_medical)

    await update.message.reply_text(answer)
    await show_continue_options(update, context)

async def show_continue_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает опции продолжения после ответа"""
    profile_id = context.user_data.get('selected_profile_id')
    
    if profile_id:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❓ Задать еще вопрос", callback_data=f"ask_question_{profile_id}")],
            [InlineKeyboardButton("📋 Назад к анкете", callback_data=f"view_profile_{profile_id}")],
        ])
        await update.message.reply_text("Что дальше?", reply_markup=keyboard)
    else:
        await update.message.reply_text(
            "Вы можете задать другой вопрос или вернуться в меню 🦔:",
            reply_markup=CONTINUE_QUESTION_MARKUP
        )

async def handle_cancel_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает отмену вопроса"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("cancel_question_"):
        profile_id = int(query.data.split("_")[2])
        
        if 'waiting_for_profile_question' in context.user_data:
            del context.user_data['waiting_for_profile_question']
        
        conn = None
        try:
            conn = await get_db_connection()
            profile = await conn.fetchrow(
                "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            
            if profile:
                await show_profile_detail(query, context, dict(profile))
            else:
                await query.edit_message_text("❌ Анкета не найдена")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
        finally:
            if conn:
                await conn.close()



async def analyze_weight_by_breed(profile_data: dict) -> str:
    """Анализирует вес ежа в соответствии с породной нормой"""
    breed = profile_data.get('hedgehog_breed', '')
    weight = profile_data.get('hedgehog_weight', 0)
    age = profile_data.get('hedgehog_age', 0)
    pet_name = profile_data.get('pet_name', 'ежик')
    
    # Получаем стандарты для породы или используем дефолтные
    standards = BREED_STANDARDS.get(breed, DEFAULT_STANDARDS)
    
    # Определяем возрастную категорию
    if age < 2:
        age_category = "новорождённый"
        min_weight = standards['newborn_min']
        max_weight = standards['newborn_max']
    elif 2 <= age < standards['adult_age']:
        age_category = "подросток"
        min_weight = standards['teen_min']
        max_weight = standards['teen_max']
    else:
        age_category = "взрослый"
        min_weight = standards['adult_min']
        max_weight = standards['adult_max']
    
    # Анализ веса
    if weight < min_weight:
        status = "❌ НЕДОСТАТОЧНЫЙ ВЕС"
        advice = f"Рекомендуется консультация ветеринара. Вес ниже нормы для этого возраста и породы ежа."
    elif min_weight <= weight <= max_weight:
        status = "✅ НОРМА"
        advice = f"Вес соответствует породной норме для этого возраста."
    elif weight <= standards['max_weight']:
        status = "⚠️ ВЕРХНЯЯ ГРАНИЦА НОРМЫ"
        advice = "Вес близок к максимальному для породы. Рекомендуется следить за питанием."
    else:
        status = "🚨 ИЗБЫТОЧНЫЙ ВЕС"
        advice = "Вес превышает породную норму. Необходима консультация ветеринара и коррекция питания."
    
    # Дополнительные предупреждения для конкретных пород
    special_warnings = ""
    if breed == "Африканский карликовый" and age >= 6 and weight > 700:
        special_warnings = "\n\n⚠️ Африканские карликовые ежи склонны к ожирению. Вес >700 г требует контроля питания."
    elif breed == "Ушастый" and age >= 6 and weight > 500:
        special_warnings = "\n\n⚠️ Ушастые ежи должны быть легкими и подвижными. Вес >500 г может указывать на проблемы."
    elif breed == "Европейский" and age >= 6 and weight < 500:
        special_warnings = "\n\n💤 Европейские ежи перед спячкой могут терять вес, но ниже 500 г - это критично."
    
    # Формируем отчет
    report = f"""
🌿 **АНАЛИЗ ВЕСА: {pet_name}**

**Порода:** {breed}
**Возраст:** {age} месяцев ({age_category})
**Текущий вес:** {weight} г

**Породная норма для {age_category} возраста:**
• Минимальный: {min_weight} г
• Максимальный: {max_weight} г
• Рекомендуемый диапазон: {min_weight}-{max_weight} г

**СТАТУС:** {status}

**Рекомендация:** {advice}{special_warnings}

**Ожидаемая продолжительность жизни:** {standards['life_expectancy']}
"""
    
    return report

async def handle_weight_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает проверку веса по породной норме"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("check_weight_"):
        profile_id = int(query.data.split("_")[2])
        
        conn = None
        try:
            conn = await get_db_connection()
            profile = await conn.fetchrow(
                "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            
            if profile:
                profile_data = dict(profile)
                
                # Показываем сообщение о загрузке
                await query.edit_message_text("🔍 Анализирую данные по породным нормам...")
                
                # Генерируем анализ
                analysis = await analyze_weight_by_breed(profile_data)
                
                # Добавляем кнопку возврата
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Назад к анкете", callback_data=f"view_profile_{profile_id}")],
                ])
                
                await query.edit_message_text(analysis, reply_markup=keyboard, parse_mode='Markdown')
                
            else:
                await query.edit_message_text("❌ Анкета не найдена")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при анализе: {e}")
        finally:
            if conn:
                await conn.close()


#ГЕНЕРАЦИЯ ОТВЕТА
async def get_gigachat_token():
    """Получает access_token для GigaChat"""
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Authorization": f"Basic {GIGACHAT_API_KEY}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(uuid.uuid4())
                },
                data={"scope": "GIGACHAT_API_PERS"},
                timeout=10.0
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                return result['access_token']
            else:
                print(f"Ошибка авторизации: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"Ошибка получения токена: {e}")
        return None
    
async def retry_with_backoff(func, *args, max_attempts=3, initial_delay=1):
    attempt = 0
    while attempt < max_attempts:
        try:
            return await func(*args)
        except Exception as e:
            print(f"Ошибка ({attempt+1}/{max_attempts}): {e}. Повторная попытка...")
            await asyncio.sleep(initial_delay * (2**attempt))
            attempt += 1
    raise Exception("Все попытки исчерпаны")

async def classify_question(question: str) -> str:
    """Классифицирует вопрос на general, medical или critical"""
    access_token = await get_gigachat_token()
    if not access_token:
        return 'general'
    
    prompt = f"""
Классифицируй вопрос пользователя о еже на один из типов: 
'general' (общий уход), 
'medical' (здоровье, неэкстренные симптомы), 
'critical' (критические, угрожающие жизни симптомы: кровь, судороги, отказ органов, тяжелые травмы).

Вопрос: "{question}"

Ответь только одним словом: general, medical или critical.
"""
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(  # УБИРАЕМ retry_with_backoff
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "GigaChat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 10,  # Увеличиваем немного
                    "temperature": 0.1
                },
                timeout=10.0
            )
            
            result = response.json()
            classification = result['choices'][0]['message']['content'].strip().lower()
            
            # УПРОЩЕННАЯ ПРОВЕРКА
            if 'critical' in classification:
                return 'critical'
            elif 'medical' in classification:
                return 'medical'
            else:
                return 'general'
                
    except Exception as e:
        print(f"Ошибка классификации: {e}")
        return 'general'

async def generate_answer(question: str, profile_data: dict, is_medical: bool = False) -> str:
    """Генерирует ответ на вопрос с учетом данных ежа"""
    access_token = await get_gigachat_token()
    if not access_token:
        return "Извините, сервис временно недоступен"
    
    breed_info = f"Порода: {profile_data.get('hedgehog_breed', '')}"
    age_info = f"Возраст: {profile_data.get('hedgehog_age', '')} месяцев" if profile_data.get('hedgehog_age') else ""
    weight_info = f"Вес: {profile_data.get('hedgehog_weight', '')} грамм" if profile_data.get('hedgehog_weight') else ""
    pet_name_info = f"Кличка: {profile_data.get('pet_name', '')}" if profile_data.get('pet_name') else ""
    
    # Собираем все доступные данные
    profile_fields = [pet_name_info, breed_info, age_info, weight_info]
    profile_text = ", ".join([info for info in profile_fields if info])
    
    if is_medical:
        prompt = f"""
Ты ветеринар-ратолог, специалист по болезням ежей. Пользователь обратился с вопросом о состоянии здоровья своего питомца.

В начале своего ответа ОБЯЗАТЕЛЬНО размести следующий дисклеймер:
"⚠️ Похоже, это медицинский вопрос. Я не могу заменить помощь специалиста. Информация ниже носит только справочный характер и не заменяет консультацию ветеринара. Пожалуйста, как можно скорее обратитесь к ратологу или герпетологу."

Затем дай краткие рекомендации по первой помощи, но подчеркни необходимость срочного обращения к ветеринару-ратологу.

Вопрос: "{question}"
Данные о еже: {profile_text}
"""
    else:
        prompt = f"""
Ты консультант по содержанию ежей. Ответь на вопрос развернуто, но простым языком.

Вопрос: "{question}"
Данные о еже: {profile_text}
"""
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "GigaChat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30.0
            )
            
            result = response.json()
            answer = result['choices'][0]['message']['content']
            
            if is_medical:
                return answer + "\n\n🚨 Немедлите с обращением к ветеринару-ратологу! Это очень важно для здоровья ежика 🦔"
            return answer
            
    except Exception as e:
        print(f"Полная ошибка генерации: {e}")
        return "Извините, произошла ошибка при генерации ответа"


#КНОПКА Задать вопрос без анкеты и ее логика работы
async def ask_general_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для кнопки '❓Задать вопрос без анкеты'."""

    context.user_data['in_general_question_mode'] = True
    if 'waiting_for_general_question' in context.user_data:
        del context.user_data['waiting_for_general_question']
    
    await update.message.reply_text(
        "Задайте, пожалуйста, ваш вопрос о ежиках. Я постараюсь ответить максимально понятно и полезно 💚",
        reply_markup=BACK_TO_MENU_MARKUP
    )

    context.user_data['waiting_for_general_question'] = True

async def handle_general_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str):
    """Обрабатывает общий вопрос без анкеты"""
    processing_message = await update.message.reply_text("🔍 Анализирую ваш вопрос...")
    
    question_type = await classify_question(question)
    
    # ОБРАБОТКА КРИТИЧЕСКИХ СЛУЧАЕВ - ВЫХОДИМ СРАЗУ
    if question_type == 'critical':
        critical_warning = (
            "🚨 В вашем вопросе обнаружены признаки критической ситуации!\n\n"
            "НЕМЕДЛЕННО обратитесь к ветеринару-ратологу или в ближайшую ветеринарную клинику!\n\n"
            "Я не могу давать рекомендации по критическим случаям, так как это может быть опасно для жизни вашего колючки."
        )
        await processing_message.edit_text(critical_warning)
        
        await update.message.reply_text(
            "Вы можете задать другой вопрос или вернуться в меню 🦔:",
            reply_markup=CONTINUE_QUESTION_MARKUP
        )
        return
    
    empty_profile = {}
    is_medical = (question_type == 'medical')
    
    answer = await generate_answer(question, empty_profile, is_medical)
    
    # Отправляем ответ и предлагаем продолжить
    await update.message.reply_text(answer)
    await update.message.reply_text(
        "Вы можете задать другой вопрос или вернуться в меню 🦔:",
        reply_markup=CONTINUE_QUESTION_MARKUP
    )
    
    context.user_data['in_general_question_mode'] = True

#КНОПКА Задать вопрос с анкетой и ее логика работы
async def ask_about_my_hedgehog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для кнопки '🦔 Задать вопрос про моего ежика'."""
    user_id = update.effective_user.id

    conn = None
    try:
        conn = await get_db_connection()
        profiles = await conn.fetch(
            "SELECT profile_id, pet_name FROM HedgehogProfiles WHERE user_id = $1 ORDER BY pet_name",
            user_id
        )

        if not profiles:
            message_text = (
                "У вас пока нет анкет ежиков 🦔.\n\n"
                "Вы можете:\n"
                "• Добавить ежика в разделе «➕ Добавить ежика»\n"  
                "• Задать общий вопрос о ежах в разделе «❓Задать вопрос без анкеты»"
            )
            await update.message.reply_text(message_text, reply_markup=MAIN_MENU_MARKUP)
            return

        keyboard = []
        for profile in profiles:
            keyboard.append([
                InlineKeyboardButton(
                    f"🦔 {profile['pet_name']}", 
                    callback_data=f"ask_about_{profile['profile_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Вернуться в главное меню", callback_data="cancel_hedgehog_selection")])

        await update.message.reply_text(
            "👇 Выберите ежика, о котором хотите спросить:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        error_text = f"❌ Ошибка при загрузке анкет: {e}"
        await update.message.reply_text(error_text, reply_markup=MAIN_MENU_MARKUP)
    finally:
        if conn:
            await conn.close()

async def handle_hedgehog_selection_for_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор конкретного ежа для вопроса"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("ask_about_"):
        profile_id = int(query.data.split("_")[2])
        
        try:
            conn = await get_db_connection()
            profile = await conn.fetchrow(
                "SELECT * FROM HedgehogProfiles WHERE profile_id = $1",
                profile_id
            )
            
            if profile:
                profile_data = dict(profile)
                context.user_data['selected_profile_id'] = profile_id
                context.user_data['current_profile'] = profile_data

                context.user_data['waiting_for_profile_question'] = True
                
                pet_name = profile_data.get('pet_name', 'ежике')
                breed = profile_data.get('hedgehog_breed', 'порода не указана')
                age = profile_data.get('hedgehog_age', 'возраст не указан')
                weight = profile_data.get('hedgehog_weight', 'вес не указан')
                
                summary_text = (
                    f"🦔 Выбран ежик: {pet_name}\n"
                    f"• Порода: {breed}\n"
                    f"• Возраст: {age} месяцев\n"
                    f"• Вес: {weight} грамм\n\n"
                    f"💬 Напишите ваш вопрос о {pet_name}:"
                )
                
                await query.edit_message_text(
                    summary_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ Назад к выбору ежика", callback_data="back_to_hedgehog_selection")]
                    ])
                )
            else:
                await query.edit_message_text("❌ Анкета не найдена")
                
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при загрузке анкеты: {e}")
        finally:
            if conn:
                await conn.close()

async def handle_cancel_hedgehog_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает отмену выбора ежа для вопроса"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_hedgehog_selection":
        await query.edit_message_text(
            "Выбор ежа отменен.",
            reply_markup=None
        )

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Главное меню:",
            reply_markup=MAIN_MENU_MARKUP
        )

async def handle_cancel_hedgehog_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает отмену вопроса в режиме 'Задать вопрос про моего ежика'"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_hedgehog_question":
        # Очищаем состояние
        if 'waiting_for_profile_question' in context.user_data:
            del context.user_data['waiting_for_profile_question']
        if 'selected_profile_id' in context.user_data:
            del context.user_data['selected_profile_id']
        if 'current_profile' in context.user_data:
            del context.user_data['current_profile']
        
        user_id = query.from_user.id
        
        try:
            conn = await get_db_connection()
            profiles = await conn.fetch(
                "SELECT profile_id, pet_name FROM HedgehogProfiles WHERE user_id = $1 ORDER BY pet_name",
                user_id
            )
            
            if profiles:
                keyboard = []
                for profile in profiles:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🦔 {profile['pet_name']}", 
                            callback_data=f"ask_about_{profile['profile_id']}"
                        )
                    ])
                
                keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data="cancel_hedgehog_selection")])

                await query.edit_message_text(
                    "👇 Выберите ежика, о котором хотите спросить:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:

                await query.edit_message_text(
                    "У вас пока нет анкет ежиков 🦔.",
                    reply_markup=MAIN_MENU_MARKUP
                )
                
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка при загрузке анкет: {e}",
                reply_markup=MAIN_MENU_MARKUP
            )
        finally:
            if conn:
                await conn.close()

async def handle_back_to_hedgehog_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает возврат к выбору ежа из режима вопроса"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_hedgehog_selection":
        if 'waiting_for_profile_question' in context.user_data:
            del context.user_data['waiting_for_profile_question']
        if 'selected_profile_id' in context.user_data:
            del context.user_data['selected_profile_id']
        if 'current_profile' in context.user_data:
            del context.user_data['current_profile']
        
        user_id = query.from_user.id
        
        try:
            conn = await get_db_connection()
            profiles = await conn.fetch(
                "SELECT profile_id, pet_name FROM HedgehogProfiles WHERE user_id = $1 ORDER BY pet_name",
                user_id
            )
            
            if profiles:
                keyboard = []
                for profile in profiles:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🦔 {profile['pet_name']}", 
                            callback_data=f"ask_about_{profile['profile_id']}"
                        )
                    ])
                
                keyboard.append([InlineKeyboardButton("⬅️ Вернуться в главное меню", callback_data="cancel_hedgehog_selection")])

                await query.edit_message_text(
                    "👇 Выберите ежика, о котором хотите спросить:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    "У вас пока нет анкет ежиков 🦔.",
                    reply_markup=MAIN_MENU_MARKUP
                )
                
        except Exception as e:
            await query.edit_message_text(
                f"❌ Ошибка при загрузке анкет: {e}",
                reply_markup=MAIN_MENU_MARKUP
            )
        finally:
            if conn:
                await conn.close()

#Обработка текста
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name
    text = update.message.text
    
    await save_user_to_db(user_id, username, first_name)

    # Проверяем, является ли сообщение кнопкой главного меню
    if text in all_menu_buttons:
        await handle_main_menu(update, context)
        return

    # Обработка вопроса с анкетой
    if context.user_data.get('waiting_for_profile_question'):
        await handle_profile_question_text(update, context)
        return

    # Обработка режима "Задать еще вопрос" после ответа
    if context.user_data.get('in_general_question_mode') and text == "❓ Задать еще вопрос":
        await ask_general_question(update, context)
        return
    
    # Если ни одно из состояний не активно - предлагаем главное меню
    await update.message.reply_text("Выберите действие из меню 👆", reply_markup=MAIN_MENU_MARKUP)

async def handle_general_question_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода вопроса без анкеты (как у других кнопок)"""
    if context.user_data.get('waiting_for_general_question'):
        context.user_data['waiting_for_general_question'] = False
        question = update.message.text
        await handle_general_question(update, context, question)
    else:
        await handle_message(update, context)

app = Application.builder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^➕ Добавить ежика$"), start_profile_form),
        CallbackQueryHandler(trigger_add_profile, pattern="^trigger_add_via_menu$"),
        CallbackQueryHandler(handle_profile_actions, pattern="^edit_profile_"),
    ],
    states={
        ASK_PET_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pet_name),
            CommandHandler('cancel', cancel_form)
        ],
        ASK_BREED: [CallbackQueryHandler(handle_breed_callback, pattern="^(breed_|show_breed_examples)")],
        ASK_AGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age),
            CommandHandler('cancel', cancel_form)
        ],
        ASK_WEIGHT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_weight),
            CommandHandler('cancel', cancel_form)
        ],
        CONFIRM_PROFILE: [MessageHandler(filters.Regex("^(✅ Да|✏️ Исправить|↩️ Заполнить заново|⬅️ Вернуться в главное меню)$"), confirm_profile)],
        EDIT_CHOICE: [CallbackQueryHandler(handle_edit_callback, pattern="^edit_"),
                      MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_choice)
                    ],
        EDIT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_field_edit)],
        EDIT_BREED: [CallbackQueryHandler(handle_breed_callback, pattern="^(breed_|show_breed_examples)")],
    },
    fallbacks=[CommandHandler('cancel', cancel_form)],
    per_message=False,
    allow_reentry=True
)

# ОБРАБОТЧИКИ
app.add_handler(CommandHandler("start", start))

app.add_handler(conv_handler)

all_menu_buttons = []
for row in MAIN_MENU_KEYBOARD:
    all_menu_buttons.extend(row)
all_menu_buttons.append("⬅️ Вернуться в главное меню")

app.add_handler(MessageHandler(filters.Text(all_menu_buttons), handle_main_menu))

app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, 
    handle_general_question_input
))

# Добавьте это после создания app
app.add_error_handler(error_handler)

app.add_handler(CallbackQueryHandler(handle_cancel_hedgehog_selection, pattern="^cancel_hedgehog_selection$"))
app.add_handler(CallbackQueryHandler(handle_cancel_hedgehog_question, pattern="^cancel_hedgehog_question$"))
app.add_handler(CallbackQueryHandler(handle_back_to_hedgehog_selection, pattern="^back_to_hedgehog_selection$"))
app.add_handler(CallbackQueryHandler(handle_weight_check, pattern="^check_weight_"))
app.add_handler(CallbackQueryHandler(handle_profile_selection, pattern="^view_profile_"))
app.add_handler(CallbackQueryHandler(handle_profile_actions, pattern="^(ask_question_|delete_)"))
app.add_handler(CallbackQueryHandler(handle_delete_confirmation, pattern="^(confirm_|cancel_)"))
app.add_handler(CallbackQueryHandler(handle_navigation, pattern="^(profiles_page_|back_to_|main_menu)"))
app.add_handler(CallbackQueryHandler(handle_noop, pattern="^noop"))
app.add_handler(CallbackQueryHandler(handle_profile_question_callback, pattern="^ask_question_"))
app.add_handler(CallbackQueryHandler(handle_cancel_question, pattern="^cancel_question_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_question_text))

app.add_handler(CallbackQueryHandler(handle_hedgehog_selection_for_question, pattern="^ask_about_"))

# ОБЩИЙ ОБРАБОТЧИК ТЕКСТА 
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


print("Бот запущен...")
app.run_polling()
