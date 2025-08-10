import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ParseMode, ReplyKeyboardRemove
from telegram.ext import (
    CallbackContext, ConversationHandler, CommandHandler, 
    MessageHandler, CallbackQueryHandler, Filters
)
from models import User, ServiceRequest, RequestStatus
from config import ADMIN_IDS, MILEAGE_ADMIN_ID
from data_store import data_store

# Define conversation states
(
    START, REGISTER, REGISTER_NAME, REGISTER_SURNAME, MAIN_MENU, FORM_CAR_BRAND,
    FORM_CAR_MODEL, FORM_CAR_YEAR, FORM_LICENSE_PLATE, FORM_MILEAGE, 
    FORM_REQUESTED_WORK, FORM_PREFERRED_DATE, FORM_PHONE, 
    FORM_CONFIRM, MY_REQUESTS, ADMIN_MENU, REQUEST_DETAILS,
    FORM_MODEL_MANUAL, FORM_REAL_NAME, FORM_REAL_SURNAME, ADMIN_NOTE,
    FORM_WORK_TYPE, FORM_WORK_MANUAL, FORM_SELECT_DATE, FORM_PHONE_CHOICE,
    MILEAGE_RESPONSE, MILEAGE_RESPONSE_TEXT  # Новые состояния для обработки запросов о пробеге предыдущего ТО
) = range(27)

# Структура марок и моделей автомобилей - УПРОЩЁННАЯ ВЕРСИЯ
# Каждая марка просто содержит список моделей с полными названиями

# Toyota модели
TOYOTA_MODELS = [
    "Corolla", "Ch-r", "Camry", "Rav4", "Highlander", "Fortuner", "Hilux",
    "Land Cruiser 200", "Land Cruiser 300", "Land Cruiser Prado"
]

# Lexus модели 
LEXUS_MODELS = [
    "IS", "IS 250", "IS 350",
    "ES 200", "ES 250", "ES 350",
    "GS 300", "GS 350",
    "UX 200", "UX 250h", 
    "NX 200", "NX 200t", "NX 300", "NX 300h",
    "RX 270", "RX 200t", "RX 300", "RX 350", "RX 450h",
    "GX 460", "GX 470", "GX 500",
    "LX 570", "LX 600"
]

# Объединяем все модели в один словарь
CAR_BRANDS = {
    "Toyota": TOYOTA_MODELS,
    "Lexus": LEXUS_MODELS
}

# Доступные годы выпуска
CAR_YEARS = list(range(2006, 2026))

def create_main_menu_keyboard():
    """Создает клавиатуру с кнопкой главного меню."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🏠 Главное меню")]],
        resize_keyboard=True
    )
    
def handle_main_menu_button(update: Update, context: CallbackContext) -> int:
    """Обработчик нажатия на кнопку Главное меню в обычной клавиатуре"""
    # Перенаправляем пользователя в главное меню
    return show_main_menu(update, context)

def start(update: Update, context: CallbackContext) -> int:
    """Start the conversation and ask if the user wants to register"""
    user = update.effective_user
    telegram_id = user.id
    
    # Check if user is already registered
    existing_user = data_store.get_user(telegram_id)
    
    if existing_user:
        return show_main_menu(update, context)
    
    update.message.reply_text(
        f"Здравствуйте, {user.first_name}! Добро пожаловать в сервис автомастерской.\n"
        "Для начала работы необходимо зарегистрироваться.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Зарегистрироваться", callback_data="register")]
        ])
    )
    
    return START

def register_callback(update: Update, context: CallbackContext) -> int:
    """Handle the registration button click"""
    query = update.callback_query
    query.answer()
    
    query.message.reply_text(
        "Для регистрации нам нужна ваша контактная информация.\n\nПожалуйста, введите ваше имя:"
    )
    
    return REGISTER_NAME

def register_name(update: Update, context: CallbackContext) -> int:
    """Save user's first name and ask for surname"""
    first_name = update.message.text.strip()
    
    # Сохраняем имя во временных данных пользователя
    context.user_data['real_first_name'] = first_name
    
    update.message.reply_text(
        f"Спасибо, {first_name}! Теперь, пожалуйста, введите вашу фамилию:"
    )
    
    return REGISTER_SURNAME

def register_surname(update: Update, context: CallbackContext) -> int:
    """Save user's surname and ask for phone number"""
    last_name = update.message.text.strip()
    
    # Сохраняем фамилию во временных данных пользователя
    context.user_data['real_last_name'] = last_name
    
    update.message.reply_text(
        "Пожалуйста, поделитесь своим номером телефона для завершения регистрации.",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Поделиться номером телефона", request_contact=True)]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    
    return REGISTER

def register_phone(update: Update, context: CallbackContext) -> int:
    """Register a new user with their phone number"""
    user = update.effective_user
    contact = update.message.contact
    
    # Получаем имя и фамилию из контекста, или используем имя и фамилию из Telegram профиля
    first_name = context.user_data.get('real_first_name', user.first_name)
    last_name = context.user_data.get('real_last_name', user.last_name)
    
    # Create a new user
    new_user = User(
        telegram_id=user.id,
        username=user.username,
        first_name=first_name,
        last_name=last_name,
        phone=contact.phone_number if contact else update.message.text
    )
    
    data_store.add_user(new_user)
    
    update.message.reply_text(
        f"Спасибо за регистрацию, {first_name}! Теперь вы можете пользоваться сервисом."
    )
    
    # Очищаем временные данные
    if 'real_first_name' in context.user_data:
        del context.user_data['real_first_name']
    if 'real_last_name' in context.user_data:
        del context.user_data['real_last_name']
    
    return show_main_menu(update, context)

def show_main_menu(update: Update, context: CallbackContext) -> int:
    """Show the main menu with options"""
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS
    
    buttons = [
        [InlineKeyboardButton("📝 Создать заявку", callback_data="new_request")],
        [InlineKeyboardButton("🔍 Мои заявки", callback_data="my_requests")],
    ]
    
    if is_admin:
        buttons.append([InlineKeyboardButton("👨‍💼 Администрирование", callback_data="admin_menu")])
    
    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    # Add the keyboard with Main Menu button
    keyboard = create_main_menu_keyboard()
    
    if hasattr(update, 'callback_query') and update.callback_query:
        update.callback_query.answer()
        update.callback_query.message.edit_text(
            "Главное меню. Выберите действие:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        # Просто устанавливаем клавиатуру без дополнительного сообщения
        update.callback_query.message.reply_text(
            "🏠 Быстрый доступ к меню:",
            reply_markup=keyboard
        )
    else:
        update.message.reply_text(
            "Главное меню. Выберите действие:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        # Просто устанавливаем клавиатуру без дополнительного сообщения
        # Для новых пользователей показываем краткую подсказку        
        if not data_store.get_user(update.effective_user.id):
            update.message.reply_text(
                "🏠 Быстрый доступ к меню:",
                reply_markup=keyboard
            )
    
    return MAIN_MENU

def start_new_request(update: Update, context: CallbackContext) -> int:
    """Start the service request form by showing car brands"""
    query = update.callback_query
    query.answer()
    
    # Создаем клавиатуру с марками Toyota и Lexus
    buttons = [
        [InlineKeyboardButton("Lexus", callback_data="brand_Lexus")],
        [InlineKeyboardButton("Toyota", callback_data="brand_Toyota")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    
    query.message.edit_text(
        "Создание новой заявки на обслуживание автомобиля\n\n"
        "Выберите марку вашего автомобиля:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return FORM_CAR_BRAND

def process_car_brand(update: Update, context: CallbackContext) -> int:
    """Process car brand selection and show year selection"""
    query = update.callback_query
    query.answer()
    
    # Получаем выбранную марку из callback_data
    brand_data = query.data.split('_', 1)[1]
    
    # Функция выбора "Другая марка" отключена
    
    # Сохраняем выбранную марку
    context.user_data['car_brand'] = brand_data
    
    # Сразу показываем выбор года выпуска после выбора марки
    query.message.edit_text(
        f"Выбрана марка: {brand_data}\n\n"
        "Теперь выберите год выпуска вашего автомобиля:",
        reply_markup=InlineKeyboardMarkup(create_year_buttons())
    )
    
    return FORM_CAR_YEAR

def process_car_model_selection(update: Update, context: CallbackContext) -> int:
    """Process car model selection and proceed to license plate entry"""
    query = update.callback_query
    query.answer()
    
    # Получаем выбранную модель из callback_data
    callback_data = query.data.split('_', 1)[1]
    
    # Если пользователь выбрал "Другая модель"
    if "other" in callback_data.lower():
        query.message.edit_text(
            f"Выбрана марка: {context.user_data['car_brand']}\n"
            f"Выбран год: {context.user_data['car_year']}\n\n"
            "Пожалуйста, введите модель вашего автомобиля:"
        )
        return FORM_MODEL_MANUAL
    
    car_brand = context.user_data['car_brand']
    car_year = context.user_data['car_year']
    
    # Преобразуем callback_data с подчеркиваниями обратно в пробелы
    # для моделей с пробелами, например "Land_Cruiser_200" -> "Land Cruiser 200"
    selected_model = callback_data.replace("_", " ")
    
    # Проверяем, есть ли такая модель в списке моделей марки
    valid_model = False
    for model in CAR_BRANDS[car_brand]:
        if model.lower() == selected_model.lower():
            selected_model = model  # Используем оригинальное написание из списка для сохранения регистра
            valid_model = True
            break
    
    if not valid_model:
        # Если модель не найдена, это может быть ошибкой
        logging.error(f"Model {selected_model} not found in brand {car_brand}")
    
    # Формируем полное название автомобиля для отображения
    context.user_data['car_model'] = f"{car_brand} {selected_model} {car_year} г."
    
    # Переходим к вводу регистрационного номера
    query.message.edit_text(
        f"Автомобиль: {context.user_data['car_model']}\n\n"
        "Теперь введите государственный номер автомобиля:"
    )
    
    return FORM_LICENSE_PLATE

# Убираем функцию process_car_submodel, так как теперь она не нужна.
# Все модели теперь находятся в одном списке с полными названиями.

def process_model_manual(update: Update, context: CallbackContext) -> int:
    """Process manually entered car model"""
    car_model = update.message.text
    
    # Если был выбран год перед ручным вводом модели
    if 'car_brand' in context.user_data and 'car_year' in context.user_data:
        car_brand = context.user_data['car_brand']
        car_year = context.user_data['car_year']
        
        # Формируем полное название с учётом марки и года
        context.user_data['car_model'] = f"{car_brand} {car_model} {car_year} г."
        
        # Сразу переходим к вводу номера
        update.message.reply_text(
            f"Автомобиль: {context.user_data['car_model']}\n\n"
            "Теперь введите государственный номер автомобиля:"
        )
        
        return FORM_LICENSE_PLATE
    else:
        # Если это прямой ручной ввод (например, после "другая марка")
        context.user_data['car_model'] = car_model
        
        # Переходим к выбору года
        keyboard = create_main_menu_keyboard()
        
        update.message.reply_text(
            f"Автомобиль: {car_model}\n\n"
            "Теперь выберите год выпуска вашего автомобиля:",
            reply_markup=InlineKeyboardMarkup(create_year_buttons())
        )
        
        return FORM_CAR_YEAR

def show_car_year_selection(update: Update, context: CallbackContext) -> int:
    """Show car year selection buttons"""
    query = update.callback_query
    
    query.message.edit_text(
        f"Автомобиль: {context.user_data['car_model']}\n\n"
        "Теперь выберите год выпуска вашего автомобиля:",
        reply_markup=InlineKeyboardMarkup(create_year_buttons())
    )
    
    return FORM_CAR_YEAR

def create_year_buttons():
    """Create buttons for year selection"""
    buttons = []
    years_per_row = 4
    
    # Группируем года по 4 в ряд
    for i in range(0, len(CAR_YEARS), years_per_row):
        row = []
        for year in CAR_YEARS[i:i+years_per_row]:
            row.append(InlineKeyboardButton(str(year), callback_data=f"year_{year}"))
        buttons.append(row)
    
    # Добавляем кнопку "Назад"
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="new_request")])
    
    return buttons

def process_car_year(update: Update, context: CallbackContext) -> int:
    """Process car year selection and proceed to model selection"""
    query = update.callback_query
    query.answer()
    
    # Получаем выбранный год из callback_data
    year = query.data.split('_', 1)[1]
    
    # Сохраняем выбранный год
    context.user_data['car_year'] = year
    
    car_brand = context.user_data['car_brand']
    
    # Получаем все модели выбранной марки
    all_models = CAR_BRANDS[car_brand]
    
    # Создаем клавиатуру для отображения всех моделей
    # Размещаем модели в отдельных кнопках для лучшей читаемости
    buttons = []
    for model in all_models:
        # Заменяем пробелы в callback_data на подчеркивания для моделей с пробелами
        model_key = model.replace(" ", "_")
        buttons.append([InlineKeyboardButton(model, callback_data=f"model_{model_key}")])
    
    # Добавляем опцию для выбора другой модели
    other_model_text = f"Другая модель {car_brand}"
    buttons.append([InlineKeyboardButton(other_model_text, callback_data="model_other")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="new_request")])
    
    # Выводим сообщение с полным списком моделей
    query.message.edit_text(
        f"Выбрана марка: {car_brand}\n"
        f"Выбран год: {year}\n\n"
        "Теперь выберите модель автомобиля:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return FORM_CAR_MODEL

def back_to_date_selection(update: Update, context: CallbackContext) -> int:
    """Обработчик кнопки 'Назад к выбору даты'"""
    query = update.callback_query
    query.answer()
    
    # Получаем выбранный тип работы из контекста
    requested_work = context.user_data.get('requested_work', 'Не указано')
    
    # Переходим к выбору даты
    now = datetime.datetime.now()
    available_dates = []
    
    # Находим дату начала следующей недели (понедельник)
    days_until_next_monday = 7 - now.weekday() if now.weekday() > 0 else 7
    next_monday = now + datetime.timedelta(days=days_until_next_monday)
    
    # Генерируем даты на ближайшие 2 месяца (60 дней), начиная со следующей недели
    for i in range(60):
        date = next_monday + datetime.timedelta(days=i)
        # Ограничиваем выбор только вторником, средой и четвергом
        if date.weekday() in [1, 2, 3]:  # 0 - понедельник, 1 - вторник, ...
            available_dates.append(date)
    
    # Создаем кнопки с датами
    buttons = []
    dates_per_row = 3
    date_buttons = []
    
    for date in available_dates[:18]:  # Ограничимся первыми 18 доступными датами
        formatted_date = date.strftime("%d.%m")
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = day_names[date.weekday()]
        button_text = f"{formatted_date} ({day_name})"
        date_key = date.strftime("%d.%m.%Y")
        date_buttons.append(InlineKeyboardButton(button_text, callback_data=f"date_{date_key}"))
        
        # Группируем даты по 3 в ряд
        if len(date_buttons) == dates_per_row:
            buttons.append(date_buttons)
            date_buttons = []
    
    # Добавляем оставшиеся даты
    if date_buttons:
        buttons.append(date_buttons)
    
    # Добавляем кнопку "Назад"
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    query.message.edit_text(
        f"Выбран тип работ: {requested_work}\n\n"
        "Выберите предпочтительную дату визита (вторник-четверг):\n"
        "❗ Дата и время предварительные\n"
        "❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return FORM_SELECT_DATE

def process_license_plate(update: Update, context: CallbackContext) -> int:
    """Save license plate and ask for mileage"""
    license_plate = update.message.text
    context.user_data['license_plate'] = license_plate
    
    update.message.reply_text(
        f"Гос. номер: {license_plate}\n\n"
        "Укажите текущий пробег автомобиля (в километрах):"
    )
    
    return FORM_MILEAGE

def process_mileage(update: Update, context: CallbackContext) -> int:
    """Save mileage and ask for requested work"""
    try:
        mileage = int(update.message.text)
        context.user_data['mileage'] = mileage
        
        # Создаем кнопки выбора типа работ
        buttons = [
            [InlineKeyboardButton("🔧 Техническое обслуживание", callback_data="work_type_to")],
            [InlineKeyboardButton("🔍 Диагностика подвески", callback_data="work_type_suspension")],
            [InlineKeyboardButton("💻 Компьютерная диагностика", callback_data="work_type_computer")],
            [InlineKeyboardButton("📏 Развал-схождение", callback_data="work_type_alignment")],
            [InlineKeyboardButton("📊 Узнать пробег предыдущего техобслуживания", callback_data="work_type_mileage_info")],
            [InlineKeyboardButton("✏️ Другое (ввести вручную)", callback_data="work_type_other")],
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        
        update.message.reply_text(
            f"Пробег: {mileage} км\n\n"
            "Выберите тип необходимых работ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        return FORM_WORK_TYPE
    except ValueError:
        update.message.reply_text(
            "Пожалуйста, введите пробег в виде числа (только цифры)."
        )
        return FORM_MILEAGE

def handle_mileage_admin_response(update: Update, context: CallbackContext) -> int:
    """Обработчик нажатия кнопки 'Ответить' для запроса о пробеге"""
    query = update.callback_query
    query.answer()
    
    # Извлекаем ID пользователя из callback_data
    user_id = query.data.split('_')[2]  # mileage_respond_USER_ID
    user_id = int(user_id)
    
    # Сохраняем ID пользователя в контексте для последующего использования
    context.user_data['mileage_response_user_id'] = user_id
    
    # Запрашиваем у админа ввод информации
    query.message.edit_text(
        "Пожалуйста, введите информацию о пробеге предыдущего ТО:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="admin_menu")]
        ])
    )
    
    return MILEAGE_RESPONSE_TEXT




def process_mileage_response_text(update: Update, context: CallbackContext) -> int:
    """Обработка текстового ответа админа на запрос о пробеге"""
    # Получаем ID пользователя из контекста
    user_id = context.user_data.get('mileage_response_user_id')
    
    if not user_id:
        update.message.reply_text(
            "Произошла ошибка: не найден ID пользователя для ответа.",
            reply_markup=create_main_menu_keyboard()
        )
        return MAIN_MENU
    
    # Получаем текст ответа админа
    response_text = update.message.text
    
    # Отправляем ответ пользователю
    try:
        context.bot.send_message(
            chat_id=user_id,
            text=f"📊 Информация о пробеге предыдущего ТО:\n\n{response_text}"
        )
        
        # Подтверждаем админу, что сообщение отправлено
        update.message.reply_text(
            "✅ Ваш ответ успешно отправлен пользователю!",
            reply_markup=create_main_menu_keyboard()
        )
        
        logging.info(f"Ответ о пробеге отправлен пользователю {user_id}")
    except Exception as e:
        update.message.reply_text(
            f"❌ Ошибка при отправке ответа: {e}",
            reply_markup=create_main_menu_keyboard()
        )
        logging.error(f"Не удалось отправить ответ о пробеге пользователю {user_id}: {e}")
    
    # Очищаем сохраненный ID пользователя
    if 'mileage_response_user_id' in context.user_data:
        del context.user_data['mileage_response_user_id']
    
    return MAIN_MENU




# Добавляем обработчик для кнопок выбора типа работ
def process_work_type(update: Update, context: CallbackContext) -> int:
    """Process work type selection from buttons"""
    query = update.callback_query
    query.answer()
    
    work_type = query.data.split('_', 2)[2]
    
    # Определяем тип работы на основе выбора пользователя
    work_types = {
        "to": "Техническое обслуживание",
        "suspension": "Диагностика подвески",
        "computer": "Компьютерная диагностика",
        "alignment": "Развал-схождение",
        "mileage_info": "Узнать пробег предыдущего техобслуживания",
        "other": None  # Для ручного ввода
    }
    
    # Если выбрана опция "Другое", переходим к вводу вручную
    if work_type == "other":
        query.message.edit_text(
            "Пожалуйста, опишите, какие работы требуется выполнить:"
        )
        return FORM_WORK_MANUAL
    
    # Если выбрана опция "Узнать пробег предыдущего ТО", переходим к специальной форме
    if work_type == "mileage_info":
        # Сохраняем выбранный тип работы
        context.user_data['requested_work'] = work_types[work_type]
        
        # Автоматически отправляем запрос без запроса телефона
        user = data_store.get_user(update.effective_user.id)
        
        # Используем ID пользователя в Telegram вместо телефона
        # Установим базовые значения для необходимых полей
        context.user_data['preferred_date'] = "В ближайшее время"
        context.user_data['preferred_time'] = None
        context.user_data['phone'] = user.phone if user and user.phone else "Не указан"
        
        # Формируем сообщение для подтверждения
        confirmation_text = (
            "📋 Подтвердите информацию для заявки:\n\n"
            f"🚗 Автомобиль: {context.user_data['car_model']}\n"
            f"🔢 Гос. номер: {context.user_data['license_plate']}\n"
            f"🔄 Текущий пробег: {context.user_data['mileage']} км\n"
            f"🔧 Запрос: {context.user_data['requested_work']}\n\n"
            "Всё верно? Мы отправим запрос специалисту, и вы получите ответ прямо в этом чате."
        )
        
        buttons = [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data="confirm"),
                InlineKeyboardButton("❌ Отменить", callback_data="cancel")
            ]
        ]
        
        query.message.edit_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        return FORM_CONFIRM
    
    # Сохраняем выбранный тип работы для остальных типов
    context.user_data['requested_work'] = work_types[work_type]
    
    # Переходим к выбору даты
    now = datetime.datetime.now()
    available_dates = []
    
    # Находим дату начала следующей недели (понедельник)
    days_until_next_monday = 7 - now.weekday() if now.weekday() > 0 else 7
    next_monday = now + datetime.timedelta(days=days_until_next_monday)
    
    # Генерируем даты на ближайшие 2 месяца (60 дней), начиная со следующей недели
    for i in range(60):
        date = next_monday + datetime.timedelta(days=i)
        # Ограничиваем выбор только вторником, средой и четвергом
        if date.weekday() in [1, 2, 3]:  # 0 - понедельник, 1 - вторник, ...
            available_dates.append(date)
    
    # Создаем кнопки с датами
    buttons = []
    dates_per_row = 3
    date_buttons = []
    
    for date in available_dates[:18]:  # Ограничимся первыми 18 доступными датами
        formatted_date = date.strftime("%d.%m")
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = day_names[date.weekday()]
        button_text = f"{formatted_date} ({day_name})"
        date_key = date.strftime("%d.%m.%Y")
        date_buttons.append(InlineKeyboardButton(button_text, callback_data=f"date_{date_key}"))
        
        # Группируем даты по 3 в ряд
        if len(date_buttons) == dates_per_row:
            buttons.append(date_buttons)
            date_buttons = []
    
    # Добавляем оставшиеся даты
    if date_buttons:
        buttons.append(date_buttons)
    
    # Добавляем кнопку "Назад"
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    query.message.edit_text(
        f"Выбран тип работ: {work_types[work_type]}\n\n"
        "Выберите предпочтительную дату визита (вторник-четверг):\n"
        "❗ Дата и время предварительные\n"
        "❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return FORM_SELECT_DATE

def process_work_manual(update: Update, context: CallbackContext) -> int:
    """Process manually entered work description"""
    work_description = update.message.text
    context.user_data['requested_work'] = work_description
    
    # Переходим к выбору даты
    now = datetime.datetime.now()
    available_dates = []
    
    # Находим дату начала следующей недели (понедельник)
    days_until_next_monday = 7 - now.weekday() if now.weekday() > 0 else 7
    next_monday = now + datetime.timedelta(days=days_until_next_monday)
    
    # Генерируем даты на ближайшие 2 месяца (60 дней), начиная со следующей недели
    for i in range(60):
        date = next_monday + datetime.timedelta(days=i)
        # Ограничиваем выбор только вторником, средой и четвергом
        if date.weekday() in [1, 2, 3]:  # 0 - понедельник, 1 - вторник, ...
            available_dates.append(date)
    
    # Создаем кнопки с датами
    buttons = []
    dates_per_row = 3
    date_buttons = []
    
    for date in available_dates[:18]:  # Ограничимся первыми 18 доступными датами
        formatted_date = date.strftime("%d.%m")
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = day_names[date.weekday()]
        button_text = f"{formatted_date} ({day_name})"
        date_key = date.strftime("%d.%m.%Y")
        date_buttons.append(InlineKeyboardButton(button_text, callback_data=f"date_{date_key}"))
        
        # Группируем даты по 3 в ряд
        if len(date_buttons) == dates_per_row:
            buttons.append(date_buttons)
            date_buttons = []
    
    # Добавляем оставшиеся даты
    if date_buttons:
        buttons.append(date_buttons)
    
    # Добавляем кнопку "Назад"
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    update.message.reply_text(
        f"Вы ввели: {work_description}\n\n"
        "Выберите предпочтительную дату визита (вторник-четверг):\n"
        "❗ Дата и время предварительные\n"
        "❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return FORM_SELECT_DATE

def process_date_selection(update: Update, context: CallbackContext) -> int:
    """Process date selection from buttons"""
    query = update.callback_query
    query.answer()
    
    date_str = query.data.split('_', 1)[1]
    context.user_data['preferred_date'] = date_str
    
    # Проверяем, есть ли у пользователя сохраненный номер телефона
    user = data_store.get_user(update.effective_user.id)
    saved_phone = user.phone if user and user.phone else None
    
    if saved_phone:
        # Предлагаем выбор между сохраненным и новым номером
        buttons = [
            [InlineKeyboardButton(f"Использовать номер: {saved_phone}", callback_data="use_saved_phone")],
            [InlineKeyboardButton("Ввести другой номер", callback_data="enter_new_phone")]
        ]
        
        query.message.edit_text(
            f"Выбрана дата: {context.user_data['preferred_date']}\n\n"
            "❗ Дата предварительная\n"
            "❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник\n\n"
            "Выберите номер телефона для связи:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        return FORM_PHONE_CHOICE
    else:
        # Если сохраненного номера нет, просим ввести номер как обычно
        query.message.edit_text(
            f"Выбрана дата: {context.user_data['preferred_date']}\n\n"
            "❗ Дата предварительная\n"
            "❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник\n\n"
            "Теперь введите ваш контактный телефон:"
        )
        
        return FORM_PHONE

def process_time_selection(update: Update, context: CallbackContext) -> int:
    """Process time selection from buttons"""
    query = update.callback_query
    query.answer()
    
    time_str = query.data.split('_', 1)[1]
    context.user_data['preferred_time'] = time_str
    
    # Проверяем, есть ли у пользователя сохраненный номер телефона
    user = data_store.get_user(update.effective_user.id)
    saved_phone = user.phone if user and user.phone else None
    
    if saved_phone:
        # Предлагаем выбор между сохраненным и новым номером
        buttons = [
            [InlineKeyboardButton(f"Использовать номер: {saved_phone}", callback_data="use_saved_phone")],
            [InlineKeyboardButton("Ввести другой номер", callback_data="enter_new_phone")]
        ]
        
        query.message.edit_text(
            f"Выбрана дата: {context.user_data['preferred_date']} в {time_str}\n\n"
            "❗ Дата и время предварительные\n"
            "❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник\n\n"
            "Выберите номер телефона для связи:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        return FORM_PHONE_CHOICE
    else:
        # Если сохраненного номера нет, просим ввести номер как обычно
        query.message.edit_text(
            f"Выбрана дата: {context.user_data['preferred_date']} в {time_str}\n\n"
            "❗ Дата и время предварительные\n"
            "❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник\n\n"
            "Теперь введите ваш контактный телефон:"
        )
        
        return FORM_PHONE

def process_phone_choice(update: Update, context: CallbackContext) -> int:
    """Process phone number choice"""
    query = update.callback_query
    query.answer()
    
    if query.data == "use_saved_phone":
        # Используем сохраненный номер
        # Получаем телефон из сохраненных данных пользователя
        user = data_store.get_user(update.effective_user.id)
        if user and user.phone:
            context.user_data['phone'] = user.phone
            
            # Переходим к подтверждению
            user_data = context.user_data
            
            confirmation_text = (
                "📋 Подтвердите информацию для заявки:\n\n"
                f"🚗 Автомобиль: {user_data['car_model']}\n"
                f"🔢 Гос. номер: {user_data['license_plate']}\n"
                f"🔄 Пробег: {user_data['mileage']} км\n"
                f"🔧 Требуемые работы: {user_data['requested_work']}\n"
                f"📅 Дата: {user_data['preferred_date']} (предварительно)\n"
                f"❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник\n"
                f"📞 Телефон: {user_data['phone']}\n\n"
                "Всё верно?"
            )
            
            buttons = [
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data="confirm"),
                    InlineKeyboardButton("❌ Отменить", callback_data="cancel")
                ]
            ]
            
            query.message.edit_text(
                confirmation_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            
            return FORM_CONFIRM
    
    # Если нет сохраненного телефона или выбрано "Ввести другой номер"
    query.message.edit_text(
        "Пожалуйста, введите ваш контактный телефон:"
    )
    return FORM_PHONE


def process_phone(update: Update, context: CallbackContext) -> int:
    """Save phone and show confirmation"""
    phone = update.message.text
    context.user_data['phone'] = phone
    
    return show_confirmation(update, context)

def show_confirmation(update: Update, context: CallbackContext) -> int:
    """Show the form summary and ask for confirmation"""
    user_data = context.user_data
    
    confirmation_text = (
        "📋 Подтвердите информацию для заявки:\n\n"
        f"🚗 Автомобиль: {user_data['car_model']}\n"
        f"🔢 Гос. номер: {user_data['license_plate']}\n"
        f"🔄 Пробег: {user_data['mileage']} км\n"
        f"🔧 Требуемые работы: {user_data['requested_work']}\n"
        f"📅 Дата: {user_data['preferred_date']} (предварительно)\n"
        f"❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник\n"
        f"📞 Телефон: {user_data['phone']}\n\n"
        "Всё верно?"
    )
    
    buttons = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel")
        ]
    ]
    
    if hasattr(update, 'message'):
        update.message.reply_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        update.callback_query.message.edit_text(
            confirmation_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    return FORM_CONFIRM

def confirm_request(update: Update, context: CallbackContext) -> int:
    """Save the service request and notify admins"""
    query = update.callback_query
    query.answer()
    
    user_data = context.user_data
    user = update.effective_user
    db_user = data_store.get_user(user.id)
    
    # Create a new service request
    new_request = ServiceRequest(
        user_id=user.id,
        car_model=user_data['car_model'],
        license_plate=user_data['license_plate'],
        mileage=user_data['mileage'],
        requested_work=user_data['requested_work'],
        preferred_date=user_data['preferred_date'],
        preferred_time=None,  # Больше не используем время
        phone=user_data['phone'],
        real_name=db_user.first_name if db_user else user.first_name,
        real_surname=db_user.last_name if db_user else user.last_name
    )
    
    # Save the request
    data_store.add_request(new_request)
    
    # Notify the user
    if user_data['requested_work'] == "Узнать пробег предыдущего техобслуживания":
        query.message.edit_text(
            "✅ Ваша заявка успешно создана!\n\n"
            "📊 Запрос о пробеге предыдущего ТО отправлен специалисту.\n"
            "Ответ будет отправлен вам как только информация будет доступна.\n\n"
            "Вы можете отслеживать статус вашей заявки в разделе 'Мои заявки'."
        )
    else:
        query.message.edit_text(
            "✅ Ваша заявка успешно создана!\n\n"
            f"📅 Предварительная дата: {user_data['preferred_date']}\n"
            "❗ Менеджер свяжется с вами для подтверждения в ближайший понедельник.\n\n"
            "Вы можете отслеживать статус вашей заявки в разделе 'Мои заявки'."
        )
    
    # Определяем, кому отправлять уведомление
    if user_data['requested_work'] == "Узнать пробег предыдущего техобслуживания" and MILEAGE_ADMIN_ID:
        # Отправляем запрос о пробеге только специальному администратору
        try:
            context.bot.send_message(
                chat_id=MILEAGE_ADMIN_ID,
                text=(
                    "📊 Новый запрос информации о пробеге предыдущего ТО!\n\n"
                    f"От: {new_request.real_name} {new_request.real_surname if new_request.real_surname else ''}\n"
                    f"Автомобиль: {new_request.car_model}\n"
                    f"Гос. номер: {new_request.license_plate}\n"
                    f"Текущий пробег: {new_request.mileage} км\n"
                    f"Телефон: {new_request.phone}"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👁 Просмотреть детали", callback_data=f"notification_view_{new_request.id}")]
                ])
            )
            
            # Уведомляем обычных администраторов о том, что заявка ушла специальному администратору
            for admin_id in ADMIN_IDS:
                if admin_id != MILEAGE_ADMIN_ID:  # Не отправляем дублирующее сообщение специальному администратору
                    context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            "📊 Новый запрос информации о пробеге предыдущего ТО\n\n"
                            f"От: {new_request.real_name} {new_request.real_surname if new_request.real_surname else ''}\n"
                            f"Автомобиль: {new_request.car_model}\n"
                            f"Гос. номер: {new_request.license_plate}\n\n"
                            "Запрос автоматически направлен специалисту по ТО."
                        )
                    )
        except Exception as e:
            logging.error(f"Error notifying mileage admin: {e}")
            # В случае ошибки, отправляем запрос всем администраторам
            for admin_id in ADMIN_IDS:
                try:
                    context.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            "📊 Новый запрос информации о пробеге предыдущего ТО!\n\n"
                            f"От: {new_request.real_name} {new_request.real_surname if new_request.real_surname else ''}\n"
                            f"Автомобиль: {new_request.car_model}\n"
                            f"Гос. номер: {new_request.license_plate}\n"
                            f"Текущий пробег: {new_request.mileage} км\n"
                            f"Телефон: {new_request.phone}\n\n"
                            "⚠️ Не удалось направить специалисту по ТО, пожалуйста, обработайте запрос."
                        ),
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("👁 Просмотреть детали", callback_data=f"notification_view_{new_request.id}")]
                        ])
                    )
                except Exception as e:
                    logging.error(f"Error notifying admin {admin_id}: {e}")
    else:
        # Для всех остальных типов заявок уведомляем всех администраторов
        for admin_id in ADMIN_IDS:
            try:
                context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "📣 Новая заявка!\n\n"
                        f"От: {new_request.real_name} {new_request.real_surname if new_request.real_surname else ''}\n"
                        f"Автомобиль: {new_request.car_model}\n"
                        f"Гос. номер: {new_request.license_plate}"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("👁 Просмотреть детали", callback_data=f"notification_view_{new_request.id}")]
                    ])
                )
            except Exception as e:
                logging.error(f"Error notifying admin {admin_id}: {e}")
    
    # Clear the form data
    context.user_data.clear()
    
    return show_main_menu(update, context)

def cancel_request(update: Update, context: CallbackContext) -> int:
    """Cancel the request form"""
    query = update.callback_query
    query.answer()
    
    try:
        query.message.edit_text(
            "❌ Заявка отменена."
        )
    except Exception as e:
        logging.error(f"Ошибка при отмене заявки: {e}")
        # Пробуем отправить новое сообщение
        query.message.reply_text(
            "❌ Заявка отменена."
        )
    
    # Clear the form data
    context.user_data.clear()
    
    return show_main_menu(update, context)

def show_my_requests(update: Update, context: CallbackContext) -> int:
    """Show the user's service requests"""
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    
    # Get user's requests
    user_requests = data_store.get_user_requests(user_id)
    
    if not user_requests:
        query.message.edit_text(
            "У вас пока нет заявок на обслуживание.\n\n"
            "Нажмите кнопку 'Создать заявку' в главном меню, чтобы создать новую заявку.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ])
        )
        return MAIN_MENU
    
    # Create buttons for each request
    buttons = []
    for request in sorted(user_requests, key=lambda r: r.created_at, reverse=True):
        status_emoji = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌",
            "completed": "🏁"
        }.get(request.status, "❓")
        
        date_created = request.created_at.strftime("%d.%m.%Y")
        
        buttons.append([
            InlineKeyboardButton(
                f"{status_emoji} {request.car_model} ({date_created})",
                callback_data=f"user_request_{request.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    query.message.edit_text(
        "Ваши заявки на обслуживание:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return MY_REQUESTS

def show_request_details(update: Update, context: CallbackContext) -> int:
    """Show details of a specific request"""
    query = update.callback_query
    query.answer()
    
    request_id = query.data.split('_', 2)[2]
    request = data_store.get_request(request_id)
    
    if not request:
        query.message.edit_text(
            "Заявка не найдена.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="my_requests")]
            ])
        )
        return MY_REQUESTS
    
    status_text = {
        "pending": "⏳ Ожидает рассмотрения",
        "approved": "✅ Принята в работу",
        "rejected": "❌ Отклонена",
        "completed": "🏁 Выполнена"
    }.get(request.status, "❓ Неизвестно")
    
    if request.requested_work == "Узнать пробег предыдущего техобслуживания":
        details_text = (
            f"📋 Запрос информации #{request.id[:8]}...\n\n"
            f"Статус: {status_text}\n"
            f"Создан: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🚗 Автомобиль: {request.car_model}\n"
            f"🔢 Гос. номер: {request.license_plate}\n"
            f"🔄 Текущий пробег: {request.mileage} км\n"
            f"🔍 Тип запроса: Информация о пробеге предыдущего ТО\n"
        )
        if request.status == "pending":
            details_text += f"\n⏳ Ваш запрос обрабатывается специалистом.\n"
    else:
        details_text = (
            f"📋 Заявка #{request.id[:8]}...\n\n"
            f"Статус: {status_text}\n"
            f"Создана: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"🚗 Автомобиль: {request.car_model}\n"
            f"🔢 Гос. номер: {request.license_plate}\n"
            f"🔄 Пробег: {request.mileage} км\n"
            f"🔧 Требуемые работы: {request.requested_work}\n"
            f"📅 Желаемая дата: {request.preferred_date} (предварительно)\n"
            f"⚠️ Менеджер свяжется с вами для подтверждения в ближайший понедельник\n"
            f"📞 Телефон: {request.phone}\n"
        )
    
    if request.admin_notes:
        details_text += f"\n📝 Комментарий мастера:\n{request.admin_notes}\n"
    
    buttons = []
    
    # Если это запрос о пробеге предыдущего ТО и есть комментарий администратора, 
    # то это значит, что у нас есть информация о пробеге
    if request.requested_work == "Узнать пробег предыдущего техобслуживания" and request.admin_notes:
        details_text = details_text.replace("Комментарий мастера:", "📊 Информация о предыдущем ТО:")
    
    buttons.append([InlineKeyboardButton("🔙 Назад к заявкам", callback_data="my_requests")])
    
    query.message.edit_text(
        details_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return MY_REQUESTS

def show_admin_menu(update: Update, context: CallbackContext) -> int:
    """Show the admin menu with options"""
    query = update.callback_query
    query.answer()
    
    buttons = [
        [InlineKeyboardButton("📥 Новые заявки", callback_data="admin_requests_pending")],
        [InlineKeyboardButton("🏁 Выполненные заявки", callback_data="admin_requests_completed")],
        [InlineKeyboardButton("📊 Запросы о пробеге", callback_data="admin_mileage_requests")],
        [InlineKeyboardButton("🔙 Вернуться в главное меню", callback_data="main_menu")]
    ]
    
    try:
        query.message.edit_text(
            "👨‍💼 Панель администратора.\n\n"
            "Выберите категорию заявок для просмотра:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logging.error(f"Ошибка при показе админ-меню: {e}")
        # Отправляем новое сообщение вместо редактирования
        query.message.reply_text(
            "👨‍💼 Панель администратора.\n\n"
            "Выберите категорию заявок для просмотра:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    return ADMIN_MENU

def show_admin_requests(update: Update, context: CallbackContext) -> int:
    """Show requests with a specific status to the admin"""
    query = update.callback_query
    query.answer()
    
    callback_data = query.data
    
    # Проверяем, если это запрос на показ запросов о пробеге
    if callback_data == "admin_mileage_requests":
        # Получаем все запросы и фильтруем только те, которые о пробеге и имеют статус PENDING
        all_requests = data_store.get_all_requests()
        # Фильтруем запросы: должны быть о пробеге и иметь статус PENDING
        mileage_requests = [
            r for r in all_requests 
            if r.requested_work == "Узнать пробег предыдущего техобслуживания" and r.status == RequestStatus.PENDING.value
        ]
        
        if not mileage_requests:
            query.message.edit_text(
                "Нет запросов о пробеге предыдущего ТО.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
            return ADMIN_MENU
            
        # Сортируем запросы - новейшие сначала
        mileage_requests.sort(key=lambda r: r.created_at, reverse=True)
        
        # Создаем кнопки для каждого запроса
        buttons = []
        for request in mileage_requests:
            user = data_store.get_user(request.user_id)
            user_name = f"{user.first_name} {user.last_name}" if user else "Неизвестный"
            
            date_created = request.created_at.strftime("%d.%m.%Y")
            
            buttons.append([
                InlineKeyboardButton(
                    f"{request.car_model} - {user_name} ({date_created}) - {request.status}",
                    callback_data=f"admin_view_{request.id}"
                )
            ])
        
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
        
        try:
            query.message.edit_text(
                "Список запросов о пробеге предыдущего ТО:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logging.error(f"Ошибка при показе списка запросов о пробеге: {e}")
            query.message.reply_text(
                "Список запросов о пробеге предыдущего ТО:",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        
        return ADMIN_MENU
    
    # Обычная обработка запросов по статусу
    status = query.data.split('_')[-1]
    
    # Get requests by status
    # Для новых заявок (pending) исключаем запросы о пробеге, так как они должны быть только в разделе "Запросы о пробеге"
    if status == "pending":
        all_pending = data_store.get_requests_by_status(status)
        # Фильтруем, исключая запросы о пробеге
        requests_list = [r for r in all_pending if r.requested_work != "Узнать пробег предыдущего техобслуживания"]
    else:
        requests_list = data_store.get_requests_by_status(status)
    
    status_text = {
        "pending": "новых",
        "approved": "одобренных",
        "rejected": "отклоненных",
        "completed": "выполненных"
    }.get(status, "")
    
    if not requests_list:
        query.message.edit_text(
            f"Нет {status_text} заявок.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
            ])
        )
        return ADMIN_MENU
    
    # Sort requests - newest first
    requests_list.sort(key=lambda r: r.created_at, reverse=True)
    
    # Create buttons for each request
    buttons = []
    for request in requests_list:
        user = data_store.get_user(request.user_id)
        user_name = f"{user.first_name} {user.last_name}" if user else "Неизвестный"
        
        date_created = request.created_at.strftime("%d.%m.%Y")
        
        buttons.append([
            InlineKeyboardButton(
                f"{request.car_model} - {user_name} ({date_created})",
                callback_data=f"admin_view_{request.id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
    
    try:
        query.message.edit_text(
            f"Список {status_text} заявок:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logging.error(f"Ошибка при показе списка заявок: {e}")
        # Отправляем новое сообщение вместо редактирования
        query.message.reply_text(
            f"Список {status_text} заявок:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    return ADMIN_MENU

def admin_view_request(update: Update, context: CallbackContext) -> int:
    """Show request details to an admin with action buttons"""
    query = update.callback_query
    query.answer()
    
    logging.info(f"Processing admin_view_request with callback data: {query.data}")
    try:
        request_id = query.data.split('_', 2)[2]
        logging.info(f"Extracted request_id: {request_id}")
    except (IndexError, ValueError) as e:
        logging.error(f"Error extracting request_id from callback data '{query.data}': {e}")
        query.message.edit_text(
            "Ошибка при обработке ID заявки.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
            ])
        )
        return ADMIN_MENU

    logging.info(f"Attempting to get request with ID: {request_id}")
    request = data_store.get_request(request_id)
    logging.info(f"Result from data_store.get_request: {request}")

    
    if not request:
        try:
            query.message.edit_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка при отображении сообщения о ненайденной заявке: {e}")
            # Пробуем отправить новое сообщение
            query.message.reply_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
        return ADMIN_MENU
    
    # Get user information
    user = data_store.get_user(request.user_id)
    
    # Используем real_name и real_surname из заявки, если они есть
    if request.real_name and request.real_surname:
        user_name = f"{request.real_name} {request.real_surname}"
    elif request.real_name:  # Если есть только имя
        user_name = request.real_name
    else:  # Запасной вариант - используем данные из профиля пользователя
        user_name = f"{user.first_name} {user.last_name}" if user else "Неизвестный пользователь"
    
    status_text = {
        "pending": "⏳ Ожидает рассмотрения",
        "approved": "✅ Принята в работу",
        "rejected": "❌ Отклонена",
        "completed": "🏁 Выполнена"
    }.get(request.status, "❓ Неизвестно")
    
    if request.requested_work == "Узнать пробег предыдущего техобслуживания":
        details_text = (
            f"📊 Запрос информации о пробеге #{request.id[:8]}...\n\n"
            f"Статус: {status_text}\n"
            f"Создан: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Клиент: {user_name}\n\n"
            f"🚗 Автомобиль: {request.car_model}\n"
            f"🔢 Гос. номер: {request.license_plate}\n"
            f"🔄 Текущий пробег: {request.mileage} км\n"
            f"🔍 Тип запроса: Информация о пробеге предыдущего ТО\n"
            f"📞 Телефон: {request.phone}\n"
        )
    else:
        details_text = (
            f"📋 Заявка #{request.id[:8]}...\n\n"
            f"Статус: {status_text}\n"
            f"Создана: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Клиент: {user_name}\n\n"
            f"🚗 Автомобиль: {request.car_model}\n"
            f"🔢 Гос. номер: {request.license_plate}\n"
            f"🔄 Пробег: {request.mileage} км\n"
            f"🔧 Требуемые работы: {request.requested_work}\n"
            f"📅 Желаемая дата: {request.preferred_date} (предварительно)\n"
            f"⚠️ Необходимо связаться с клиентом в ближайший понедельник перед выбранной датой\n"
            f"📞 Телефон: {request.phone}\n"
        )
    
    if request.admin_notes:
        details_text += f"\n📝 Комментарий:\n{request.admin_notes}\n"
    
    # Create action buttons based on current status
    buttons = []
    if request.requested_work == "Узнать пробег предыдущего техобслуживания":
        if request.status == RequestStatus.PENDING.value:
            buttons.append([InlineKeyboardButton("📊 Ответить о пробеге", callback_data=f"mileage_response_{request.id}")])
            buttons.append([InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_mileage_{request.id}")])
        # Для запросов о пробеге другие кнопки не добавляем, кроме "Назад"
    elif request.status == RequestStatus.PENDING.value:
        buttons.append([
            InlineKeyboardButton("✅ Принять в работу", callback_data=f"approve_{request.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{request.id}")
        ])
        buttons.append([InlineKeyboardButton("📝 Добавить комментарий", callback_data=f"comment_{request.id}")])
    elif request.status == RequestStatus.APPROVED.value:
        buttons.append([
            InlineKeyboardButton("🏁 Выполнить", callback_data=f"complete_{request.id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{request.id}")
        ])
        buttons.append([InlineKeyboardButton("📝 Добавить комментарий", callback_data=f"comment_{request.id}")])
    elif request.status == RequestStatus.COMPLETED.value:
        buttons.append([
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{request.id}")
        ])
        # Комментарий к выполненным не добавляем, т.к. есть удаление
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
    
    try:
        query.message.edit_text(
            details_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        logging.error(f"Ошибка при показе деталей заявки: {e}")
        # Отправляем новое сообщение вместо редактирования
        query.message.reply_text(
            details_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    return ADMIN_MENU

def admin_update_request(update: Update, context: CallbackContext) -> int:
    """Handle request status updates (approve, reject, complete)"""
    query = update.callback_query
    query.answer()
    
    # Разделяем callback_data, чтобы правильно обработать reject_mileage
    parts = query.data.split('_', 1)
    action = parts[0]
    request_id = parts[1]

    if action == "reject" and request_id.startswith("mileage_"):
        action = "reject_mileage"
        request_id = request_id.split('_',1)[1]

    request = data_store.get_request(request_id)
    
    if not request:
        try:
            query.message.edit_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка при отображении сообщения о ненайденной заявке: {e}")
            # Пробуем отправить новое сообщение
            query.message.reply_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
        return ADMIN_MENU
    
    # Сохраняем ID запроса в user_data для дальнейшей обработки
    context.user_data['current_request_id'] = request_id
    context.user_data['action'] = action
    
    # Подготавливаем сообщение в зависимости от действия
    if action == "approve":
        message = "Вы собираетесь ПРИНЯТЬ ЗАЯВКУ В РАБОТУ.\nВведите комментарий для клиента (или /skip чтобы пропустить):"
    elif action == "complete":
        message = "Вы собираетесь отметить заявку как ВЫПОЛНЕННУЮ.\nВведите комментарий о выполненных работах (или /skip чтобы пропустить):"
    elif action == "reject":
        message = "Вы собираетесь ОТКЛОНИТЬ заявку.\nВведите причину отказа (или /skip чтобы пропустить):"
    elif action == "reject_mileage":
        # Отклонение запроса о пробеге без комментария
        if request and request.requested_work == "Узнать пробег предыдущего техобслуживания":
            request.status = RequestStatus.REJECTED.value
            updated = data_store.update_request(request)
            if updated:
                query.message.edit_text(
                    f"Запрос о пробеге #{request_id[:8]} был отклонен.",
                    reply_markup=InlineKeyboardMarkup([ 
                        [InlineKeyboardButton("🔙 Назад к меню", callback_data="admin_menu")]
                    ])
                )
                # Уведомляем пользователя
                context.bot.send_message(
                    chat_id=request.user_id,
                    text=f"Ваш запрос о пробеге для {request.car_model} ({request.license_plate}) был отклонен администратором."
                )
            else:
                query.message.edit_text("Не удалось обновить статус заявки.")
            return ADMIN_MENU
        else:
            message = "Вы собираетесь ОТКЛОНИТЬ заявку.\nВведите причину отказа:" # Эта ветка теперь для обычных заявок
    elif action == "delete":
        message = "Вы собираетесь УДАЛИТЬ заявку.\nВведите причину удаления (или /skip чтобы пропустить):"
    elif action == "comment":
        message = "Введите комментарий к заявке:"
    else:
        # Непредвиденный случай
        query.message.edit_text(
            "Неизвестное действие.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
            ])
        )
        return ADMIN_MENU
    
    # Запрашиваем комментарий от администратора
    # Для всех действий показываем одинаковые опции
    query.message.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✖️ Без комментария", callback_data=f"no_comment_{action}")],
            [InlineKeyboardButton("🔙 Отмена", callback_data="admin_menu")]
        ])
    )
    
    return ADMIN_NOTE

def save_admin_comment(update: Update, context: CallbackContext) -> int:
    """Save admin comment and update request status"""
    
    # Получаем данные из контекста
    request_id = context.user_data.get('current_request_id')
    action = context.user_data.get('action')
    
    # Определяем, является ли это нажатием на кнопку без комментария 
    # или вводом текста пользователем
    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        query.answer()
        
        # Извлекаем действие из callback_data, если request_id и action не сохранены в контексте
        if not request_id or not action:
            action = query.data.split('_', 2)[2]  # no_comment_ACTION
            
        # Для действия "reject" проверяем, была ли нажата кнопка "Без комментария"
        if action == "reject" and query.data.startswith("no_comment_"):
            # Установка стандартной причины для кнопки "Без комментария"
            notes = "Причина не указана"
        else:
            # Для других действий и кнопок без комментария, просто пустая строка
            notes = ""
    else:
        # Если введен текстовый комментарий
        if update.message.text == "/skip":
            # Для действия "reject" теперь также разрешаем пропустить комментарий
            if action == "reject":
                notes = "Причина не указана"
            else:
                notes = ""
        else:
            # Здесь установка полученного текста как причины отказа
            notes = update.message.text
    
    # Находим запрос
    request = data_store.get_request(request_id)
    
    if not request:
        if hasattr(update, 'callback_query') and update.callback_query:
            update.callback_query.message.edit_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
        else:
            update.message.reply_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
        return ADMIN_MENU
    
    # Формируем сообщение пользователю
    user_message = ""
    admin_message = ""
    
    # Обновляем статус запроса в зависимости от действия
    if action == "approve":
        request.approve(notes)
        user_message = f"✅ Ваша заявка #{request.id[:8]} принята в работу."
        admin_message = f"✅ Заявка принята в работу."

    elif action == "reject":
        # Отклоняем заявку, но оставляем в системе
        request.reject(notes)
        data_store.update_request(request)
        
        user_message = f"❌ Ваша заявка #{request.id[:8]} отклонена. Причина: {notes}"
        admin_message = f"❌ Заявка отклонена."
    elif action == "complete":
        request.complete(notes)
        user_message = f"🏁 Ваша заявка #{request.id[:8]} выполнена."
        admin_message = f"🏁 Заявка помечена как выполненная."
    elif action == "delete":
        # Сохраняем ID и пользователя перед удалением для отправки уведомления
        request_id_short = request.id[:8]
        user_id = request.user_id
        car_model = request.car_model
        requested_work = request.requested_work
        preferred_date = request.preferred_date
        preferred_time = request.preferred_time
        
        # Полностью удаляем заявку из системы
        data_store.delete_request(request.id)
        
        # После удаления request уже нет в системе, поэтому используем сохраненные данные
        user_message = f"🗑️ Ваша заявка #{request_id_short} удалена из системы."
        admin_message = f"🗑️ Заявка полностью удалена из системы."
        
        # Обновляем user_id для отправки сообщения пользователю
        context.user_data['deleted_request_info'] = {
            'user_id': user_id,
            'request_id_short': request_id_short,
            'car_model': car_model,
            'requested_work': requested_work,
            'preferred_date': preferred_date,
            'preferred_time': preferred_time
        }
    elif action == "comment":
        request.admin_notes = notes
        data_store.update_request(request)
        user_message = f"📝 К вашей заявке #{request.id[:8]} добавлен комментарий."
        admin_message = f"📝 Комментарий добавлен."
    
    # Проверяем, была ли удалена заявка
    deleted_info = context.user_data.get('deleted_request_info')
    
    # Для случаев, когда заявка НЕ была удалена
    if action != "delete":
        # Сохраняем изменения
        data_store.update_request(request)
        
        # Уведомляем пользователя
        if user_message:
            time_str = f" в {request.preferred_time}" if request.preferred_time and request.preferred_time != "Любое время" else ""
            
            if request.requested_work == "Узнать пробег предыдущего техобслуживания":
                context.bot.send_message(
                    chat_id=request.user_id,
                    text=(
                        f"{user_message}\n\n"
                        f"🚗 {request.car_model}\n"
                        f"🔢 {request.license_plate}\n"
                        f"{f'📝 Комментарий: {notes}' if notes else ''}"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("👁 Просмотреть детали", callback_data=f"user_request_{request.id}")]
                    ])
                )
            else:
                context.bot.send_message(
                    chat_id=request.user_id,
                    text=(
                        f"{user_message}\n\n"
                        f"🚗 {request.car_model}\n"
                        f"🔧 {request.requested_work}\n"
                        f"📅 {request.preferred_date}{time_str}\n"
                        f"{f'📝 Комментарий: {notes}' if notes else ''}"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("👁 Просмотреть детали", callback_data=f"user_request_{request.id}")]
                    ])
                )

    
    # Отвечаем администратору
    if hasattr(update, 'callback_query') and update.callback_query:
        update.callback_query.message.edit_text(
            f"{admin_message}"
        )
        # Показываем обновленные детали запроса
        return admin_view_request(update, context)
    else:
        update.message.reply_text(
            f"{admin_message}"
        )
        
        # Создаем фейковый callback_query для повторного вызова admin_view_request
        class FakeUpdate:
            class FakeCallbackQuery:
                def __init__(self, data, message):
                    self.data = data
                    self.message = message
                
                def answer(self):
                    pass
            
            def __init__(self, original_update, data):
                self.callback_query = self.FakeCallbackQuery(data, original_update.message)
        
        fake_update = FakeUpdate(update, f"admin_view_{request_id}")
        return admin_view_request(fake_update, context)

def menu_command(update: Update, context: CallbackContext) -> int:
    """Команда /menu для быстрого доступа к главному меню из любого места"""
    return show_main_menu(update, context)

def handle_mileage_response(update: Update, context: CallbackContext) -> int:
    """Обработчик ответа специалиста по ТО на запрос о пробеге"""
    query = update.callback_query
    query.answer()
    
    # Извлекаем ID запроса
    request_id = query.data.split('_', 2)[2]  # mileage_response_ID
    request = data_store.get_request(request_id)
    
    if not request:
        try:
            query.message.edit_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка при отображении сообщения о ненайденной заявке: {e}")
            query.message.reply_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
        return ADMIN_MENU
    
    # Сохраняем ID запроса и ID пользователя в пользовательских данных для последующей обработки
    context.user_data['mileage_request_id'] = request_id
    context.user_data['mileage_response_user_id'] = request.user_id
    
    query.message.edit_text(
        f"📊 Ответ на запрос о пробеге предыдущего ТО\n\n"
        f"🚗 Автомобиль: {request.car_model}\n"
        f"🔢 Гос. номер: {request.license_plate}\n"
        f"🔄 Текущий пробег: {request.mileage} км\n\n"
        f"Введите информацию о предыдущем ТО, которая будет отправлена клиенту:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Отмена", callback_data="admin_menu")]
        ])
    )
    
    # Переходим в состояние ожидания ввода ответа
    return MILEAGE_RESPONSE_TEXT

def handle_mileage_response_text(update: Update, context: CallbackContext) -> int:
    """Обработка текста ответа о пробеге предыдущего ТО"""
    # Получаем ID запроса из контекста
    request_id = context.user_data.get('mileage_request_id')
    if not request_id:
        update.message.reply_text(
            "Ошибка: не найден ID запроса. Пожалуйста, начните процесс заново.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 В админ-панель", callback_data="admin_menu")]
            ])
        )
        return ADMIN_MENU
    
    # Получаем запрос
    request = data_store.get_request(request_id)
    if not request:
        update.message.reply_text(
            "Заявка не найдена.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 В админ-панель", callback_data="admin_menu")]
            ])
        )
        return ADMIN_MENU
    
    # Сохраняем ответ о пробеге как комментарий администратора
    mileage_info = update.message.text
    request.admin_notes = mileage_info
    # Сразу помечаем заявку как выполненную
    request.status = RequestStatus.COMPLETED.value 
    data_store.update_request(request)
    
    # Уведомляем клиента
    try:
        context.bot.send_message(
            chat_id=request.user_id,
            text=(
                "📊 Получена информация о пробеге предыдущего ТО:\n\n"
                f"🚗 {request.car_model}\n"
                f"🔢 {request.license_plate}\n\n"
                f"{mileage_info}"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👁 Просмотреть детали", callback_data=f"user_request_{request.id}")]
            ])
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления пользователю: {e}")
        update.message.reply_text(
            f"⚠️ Информация сохранена, но не удалось отправить уведомление пользователю: {e}"
        )
    
    # Подтверждаем специалисту, что информация отправлена и заявка выполнена
    update.message.reply_text(
        "✅ Информация о пробеге предыдущего ТО успешно отправлена клиенту, и заявка помечена как выполненная.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 В админ-панель", callback_data="admin_menu")]
        ])
    )
    
    # Очищаем контекст
    if 'mileage_request_id' in context.user_data:
        del context.user_data['mileage_request_id']
    if 'mileage_response_user_id' in context.user_data:
        del context.user_data['mileage_response_user_id']

    return ADMIN_MENU

def handle_notification_view(update: Update, context: CallbackContext) -> int:
    """Handle view request from notification buttons"""
    try:
        query = update.callback_query
        query.answer()
        
        # Используем более надежный метод извлечения ID заявки
        callback_parts = query.data.split('_')
        if len(callback_parts) < 3:
            logging.error(f"Invalid callback data format: {query.data}")
            query.message.reply_text(
                "Ошибка обработки заявки. Неверный формат данных.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
                ])
            )
            return MAIN_MENU
            
        request_id = callback_parts[2]
        logging.info(f"Viewing notification for request: {request_id}")
        
        # Получаем заявку
        request = data_store.get_request(request_id)
        
        if not request:
            logging.error(f"Request not found: {request_id}")
            query.message.reply_text(
                "Заявка не найдена.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")]
                ])
            )
            return ADMIN_MENU
        
        # Получаем информацию о пользователе
        user = data_store.get_user(request.user_id)
        
        # Используем real_name и real_surname из заявки, если они есть
        if request.real_name and request.real_surname:
            user_name = f"{request.real_name} {request.real_surname}"
        elif request.real_name:  # Если есть только имя
            user_name = request.real_name
        else:  # Запасной вариант - используем данные из профиля пользователя
            user_name = f"{user.first_name} {user.last_name}" if user else "Неизвестный пользователь"
        
        status_text = {
            "pending": "⏳ Ожидает рассмотрения",
            "approved": "✅ Одобрена",
            "rejected": "❌ Отклонена",
            "completed": "🏁 Выполнена"
        }.get(request.status, "❓ Неизвестно")
        
        time_str = f" в {request.preferred_time}" if request.preferred_time and request.preferred_time != "Любое время" else ""
        
        if request.requested_work == "Узнать пробег предыдущего техобслуживания":
            details_text = (
                f"📊 Запрос информации о пробеге #{request.id[:8]}...\n\n"
                f"Статус: {status_text}\n"
                f"Создан: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"Клиент: {user_name}\n\n"
                f"🚗 Автомобиль: {request.car_model}\n"
                f"🔢 Гос. номер: {request.license_plate}\n"
                f"🔄 Текущий пробег: {request.mileage} км\n"
                f"🔍 Тип запроса: Информация о пробеге предыдущего ТО\n"
                f"📞 Телефон: {request.phone}\n"
            )
        else:
            details_text = (
                f"📋 Заявка #{request.id[:8]}...\n\n"
                f"Статус: {status_text}\n"
                f"Создана: {request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"Клиент: {user_name}\n\n"
                f"🚗 Автомобиль: {request.car_model}\n"
                f"🔢 Гос. номер: {request.license_plate}\n"
                f"🔄 Пробег: {request.mileage} км\n"
                f"🔧 Требуемые работы: {request.requested_work}\n"
                f"📅 Желаемая дата: {request.preferred_date}{time_str} (предварительно)\n"
                f"⚠️ Необходимо связаться с клиентом в ближайший понедельник перед выбранной датой\n"
                f"📞 Телефон: {request.phone}\n"
            )
        
        if request.admin_notes:
            details_text += f"\n📝 Комментарий:\n{request.admin_notes}\n"
        
        # Создаем кнопки действий в зависимости от текущего статуса и типа запроса
        buttons = []
        
        # Не добавляем кнопки управления для запросов о пробеге (только просмотр)
        if request.requested_work != "Узнать пробег предыдущего техобслуживания":
            if request.status == RequestStatus.PENDING.value:
                buttons.append([
                    InlineKeyboardButton("✅ Принять в работу", callback_data=f"approve_{request.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{request.id}")
                ])
            elif request.status == RequestStatus.APPROVED.value:
                buttons.append([
                    InlineKeyboardButton("🏁 Выполнена", callback_data=f"complete_{request.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{request.id}")
                ])
            
            # Даем возможность добавить комментарий только если это не запрос о пробеге
            buttons.append([InlineKeyboardButton("📝 Добавить комментарий", callback_data=f"comment_{request.id}")])
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_menu")])
        
        # Используем более надежный метод отправки сообщения вместо edit_text
        try:
            query.message.edit_text(
                details_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as edit_error:
            logging.error(f"Error editing message: {edit_error}")
            # Если edit_text не работает, пробуем отправить новое сообщение
            query.message.reply_text(
                details_text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            
        logging.info(f"Successfully displayed request details for {request_id}")
        return ADMIN_MENU
        
    except Exception as e:
        logging.error(f"Error in handle_notification_view: {e}")
        try:
            update.callback_query.message.reply_text(
                "Произошла ошибка при обработке заявки. Пожалуйста, попробуйте снова.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
                ])
            )
        except:
            # Крайний случай, если совсем ничего не работает
            pass
        return MAIN_MENU

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the conversation"""
    try:
        user = update.message.from_user
        update.message.reply_text(
            f"До свидания, {user.first_name}! Надеемся увидеть вас снова."
        )
    except Exception as e:
        logging.error(f"Ошибка при отмене диалога: {e}")
        # Если не удалось отправить сообщение, просто молча завершаем диалог
    
    return ConversationHandler.END

def register_handlers(dispatcher):
    # Main conversation handler
    dispatcher.add_handler(CallbackQueryHandler(handle_mileage_admin_response, pattern=r'^mileage_respond_\d+$'))
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", menu_command),
            MessageHandler(Filters.regex("^🏠 Главное меню$"), handle_main_menu_button),
            CallbackQueryHandler(start_new_request, pattern="^new_request$"),
            CallbackQueryHandler(show_my_requests, pattern="^my_requests$"),
            CallbackQueryHandler(show_admin_menu, pattern="^admin_menu$"),
            CallbackQueryHandler(show_main_menu, pattern="^main_menu$"),
        ],
        states={
            None: [
                CallbackQueryHandler(start_new_request, pattern="^new_request$"),
                CallbackQueryHandler(show_my_requests, pattern="^my_requests$"),
                CallbackQueryHandler(show_admin_menu, pattern="^admin_menu$"),
                CallbackQueryHandler(show_main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
                CallbackQueryHandler(admin_view_request, pattern="^admin_view_"),
                CallbackQueryHandler(admin_update_request, pattern="^approve_"),
                CallbackQueryHandler(admin_update_request, pattern="^reject_"),
                CallbackQueryHandler(admin_update_request, pattern="^complete_"),
                CallbackQueryHandler(admin_update_request, pattern="^delete_"),
                CallbackQueryHandler(admin_update_request, pattern="^comment_"),
                CallbackQueryHandler(handle_mileage_response, pattern="^mileage_response_"),
                CallbackQueryHandler(show_request_details, pattern="^user_request_"),
                CallbackQueryHandler(save_admin_comment, pattern="^no_comment_"),
                CallbackQueryHandler(register_callback, pattern="^register$"),
            ],
            START: [
                CallbackQueryHandler(register_callback, pattern='^register$'),
                CallbackQueryHandler(show_main_menu, pattern="^main_menu$"),
            ],
            REGISTER_NAME: [
                MessageHandler(Filters.text & ~Filters.command, register_name)
            ],
            REGISTER_SURNAME: [
                MessageHandler(Filters.text & ~Filters.command, register_surname),
            ],
            REGISTER: [
                MessageHandler(Filters.contact | Filters.text & ~Filters.command, register_phone),
            ],
            MAIN_MENU: [
                CallbackQueryHandler(start_new_request, pattern="^new_request$"),
                CallbackQueryHandler(show_my_requests, pattern="^my_requests$"),
                CallbackQueryHandler(show_admin_menu, pattern="^admin_menu$"),
                CallbackQueryHandler(show_main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
                MessageHandler(Filters.regex("^🏠 Главное меню$"), handle_main_menu_button),
            ],
            FORM_CAR_BRAND: [
                CallbackQueryHandler(process_car_brand, pattern="^brand_"),
                CallbackQueryHandler(show_main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
            ],
            FORM_CAR_MODEL: [
                CallbackQueryHandler(process_car_model_selection, pattern="^model_"),
                CallbackQueryHandler(start_new_request, pattern="^new_request$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
            ],
            FORM_MODEL_MANUAL: [
                MessageHandler(Filters.text & ~Filters.command, process_model_manual),
            ],
            FORM_CAR_YEAR: [
                CallbackQueryHandler(process_car_year, pattern="^year_"),
                CallbackQueryHandler(start_new_request, pattern="^new_request$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
            ],
            FORM_LICENSE_PLATE: [
                MessageHandler(Filters.text & ~Filters.command, process_license_plate),
            ],
            FORM_MILEAGE: [
                MessageHandler(Filters.text & ~Filters.command, process_mileage),
            ],
            FORM_WORK_TYPE: [
                CallbackQueryHandler(process_work_type, pattern="^work_type_"),
                CallbackQueryHandler(show_main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
            ],
            FORM_WORK_MANUAL: [
                MessageHandler(Filters.text & ~Filters.command, process_work_manual),
            ],
            FORM_SELECT_DATE: [
                CallbackQueryHandler(process_date_selection, pattern=r'^date_')
            ],
            FORM_PHONE_CHOICE: [
                CallbackQueryHandler(process_phone_choice, pattern=r'^use_saved_phone$'),
                CallbackQueryHandler(process_phone_choice, pattern=r'^enter_new_phone$'),
                CallbackQueryHandler(handle_notification_view, pattern=r'^notification_view_'),
            ],
            FORM_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, process_phone),
            ],
            FORM_CONFIRM: [
                CallbackQueryHandler(confirm_request, pattern="^confirm$"),
                CallbackQueryHandler(cancel_request, pattern="^cancel$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
            ],
            MY_REQUESTS: [
                CallbackQueryHandler(show_request_details, pattern="^user_request_"),
                CallbackQueryHandler(show_main_menu, pattern="^main_menu$"),
                CallbackQueryHandler(show_my_requests, pattern="^my_requests$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
            ],
            ADMIN_MENU: [
                CallbackQueryHandler(show_admin_menu, pattern="^admin_menu$"),
                CallbackQueryHandler(show_admin_requests, pattern="^admin_requests_"),
                CallbackQueryHandler(show_admin_requests, pattern="^admin_mileage_requests$"),
                CallbackQueryHandler(admin_view_request, pattern="^admin_view_"),
                CallbackQueryHandler(admin_update_request, pattern="^approve_"),
                CallbackQueryHandler(admin_update_request, pattern="^reject_"),
                CallbackQueryHandler(admin_update_request, pattern="^complete_"),
                CallbackQueryHandler(admin_update_request, pattern="^delete_"),
                CallbackQueryHandler(admin_update_request, pattern="^comment_"),
                CallbackQueryHandler(handle_mileage_response, pattern="^mileage_response_"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
                CallbackQueryHandler(show_main_menu, pattern="^main_menu$"),
            ],
            ADMIN_NOTE: [
                MessageHandler(Filters.text & ~Filters.command, save_admin_comment),
                CommandHandler("skip", save_admin_comment),
                CallbackQueryHandler(save_admin_comment, pattern="^no_comment_"),
                CallbackQueryHandler(show_admin_menu, pattern="^admin_menu$"),
                CallbackQueryHandler(handle_notification_view, pattern="^notification_view_"),
            ],
            MILEAGE_RESPONSE_TEXT: [
                MessageHandler(Filters.text & ~Filters.command, process_mileage_response_text),
                CallbackQueryHandler(show_admin_menu, pattern=r'^admin_menu$')
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(Filters.regex("^🏠 Главное меню$"), handle_main_menu_button),
        ],
        per_chat=False,
        name="autoservice_bot",
        persistent=False,
    )
    
    dispatcher.add_handler(conv_handler)