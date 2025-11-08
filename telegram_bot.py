import telebot
from telebot import types
from datetime import datetime, timedelta

# 🔹 Твой токен и ID администратора
TOKEN = "8501555676:AAHhVVPd_uRm7arXjD87Gj74M_TZOL3xlh8"
ADMIN_ID = 692897513

bot = telebot.TeleBot(TOKEN)

# 🔹 Список услуг
services = {
    "service_1": "Стрижка - 5000 тг",
    "service_2": "Стрижка каскад (все виды) - 6000–8000 тг",
    "service_3": "Стрижка с уходом - 10 000 тг",
    "service_4": "Корни - 7000 тг",
    "service_5": "В тон до плеч - 7000 тг",
    "service_6": "В тон ниже плеч - 9000 тг",
    "service_7": "В тон ниже талии - 10 000–12 000 тг",
    "service_8": "Окрашивание маслом - 30 000 тг",
    "service_9": "Сложное окрашивание - от 40 000 тг (плюс расходный материал)",
    "service_10": "Пилинг кожи головы - 15 000 тг",
    "service_11": "«Счастье для волос» - 15 000–18 000 тг",
    "service_12": "Короткие волосы - 5000 тг",
    "service_13": "Средние волосы - 6000–7000 тг",
    "service_14": "Длинные волосы - 7000–8000 тг"
}

# 🔹 Временное хранилище
user_data = {}
bookings = {}  # { '2025-11-03': ['09:00', '10:00'] }

# 🔹 /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    for key, val in services.items():
        markup.add(types.InlineKeyboardButton(val, callback_data=key))
    bot.send_message(
        message.chat.id,
        "Здравствуйте! 💇‍♀️\n\nВыберите услугу:",
        reply_markup=markup
    )

# 🔹 выбор услуги
@bot.callback_query_handler(func=lambda call: call.data in services)
def select_service(call):
    service = services[call.data]
    user_data[call.from_user.id] = {"service": service}
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"Вы выбрали: {service}\n\nВведите ваше имя:")
    bot.register_next_step_handler(msg, ask_date)

# 🔹 запрос имени → выбор даты
def ask_date(message):
    user_id = message.from_user.id
    user_data[user_id]["name"] = message.text

    # формируем список ближайших 7 рабочих дней
    markup = types.InlineKeyboardMarkup()
    today = datetime.now()
    count = 0
    day = 0
    while count < 7:
        date = today + timedelta(days=day)
        day += 1
        if date.weekday() >= 5:  # суббота/воскресенье
            continue
        date_str = date.strftime("%d.%m.%Y")
        display = date.strftime("%a, %d %B")
        markup.add(types.InlineKeyboardButton(display, callback_data=f"date_{date_str}"))
        count += 1

    bot.send_message(message.chat.id, "Выберите дату:", reply_markup=markup)

# 🔹 выбор времени после выбора даты
@bot.callback_query_handler(func=lambda call: call.data.startswith("date_"))
def select_time(call):
    user_id = call.from_user.id
    date_str = call.data.split("_")[1]
    user_data[user_id]["date"] = date_str

    # доступные часы
    booked = bookings.get(date_str, [])
    markup = types.InlineKeyboardMarkup()

    for hour in range(9, 18):  # 9:00 - 17:00
        time_str = f"{hour:02d}:00"
        if time_str not in booked:
            markup.add(types.InlineKeyboardButton(time_str, callback_data=f"time_{time_str}"))

    if not markup.keyboard:
        bot.send_message(call.message.chat.id, "На выбранную дату все слоты заняты 😔")
        return

    bot.edit_message_text(
        f"📅 {date_str}\n\nВыберите время:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

# 🔹 выбор времени → запрос телефона
@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))
def ask_phone(call):
    user_id = call.from_user.id
    time_str = call.data.split("_")[1]
    user_data[user_id]["time"] = time_str
    date_str = user_data[user_id]["date"]

    # отмечаем слот как занятый
    if date_str not in bookings:
        bookings[date_str] = []
    bookings[date_str].append(time_str)

    # запрос телефона
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    phone_btn = types.KeyboardButton("📞 Отправить номер телефона", request_contact=True)
    markup.add(phone_btn)

    bot.send_message(
        call.message.chat.id,
        "Пожалуйста, укажите ваш номер телефона или нажмите кнопку ниже 👇",
        reply_markup=markup
    )

# 🔹 контакт через кнопку
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        bot.send_message(message.chat.id, "Пожалуйста, начните с /start")
        return
    phone = message.contact.phone_number
    user_data[user_id]["phone"] = phone
    confirm_booking(message)

# 🔹 телефон введён вручную
@bot.message_handler(func=lambda message: message.text.startswith("+"))
def handle_phone_text(message):
    user_id = message.from_user.id
    if user_id in user_data and "phone" not in user_data[user_id]:
        user_data[user_id]["phone"] = message.text
        confirm_booking(message)

# 🔹 подтверждение записи
def confirm_booking(message):
    user_id = message.from_user.id
    data = user_data[user_id]
    service = data["service"]
    name = data["name"]
    date = data["date"]
    time_str = data["time"]
    phone = data["phone"]

    confirmation_text = (
        f"✅ Ваша запись подтверждена!\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}\n"
        f"💇 Услуга: {service}\n"
        f"📅 Дата: {date}\n"
        f"🕒 Время: {time_str}\n\n"
        f"📍 Адрес: Толе би 57\n"
        f"Мы свяжемся с вами для уточнения деталей 💖"
    )

    bot.send_message(message.chat.id, confirmation_text, reply_markup=types.ReplyKeyboardRemove())

    # уведомление админу
    admin_msg = (
        f"📥 Новая запись!\n\n"
        f"👤 {name}\n📞 {phone}\n💇 {service}\n📅 {date}\n🕒 {time_str}\n📍 Толе би 57"
    )
    bot.send_message(ADMIN_ID, admin_msg)

# 🔹 команда /записи (для администратора)
@bot.message_handler(commands=['записи'])
def show_records(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет доступа.")
        return

    if not user_data:
        bot.send_message(message.chat.id, "📭 Записей пока нет.")
        return

    text = "📋 Все текущие записи:\n\n"
    for u_id, data in user_data.items():
        text += (
            f"👤 {data.get('name', '-')}\n"
            f"📞 {data.get('phone', '-')}\n"
            f"💇 {data.get('service', '-')}\n"
            f"📅 {data.get('date', '-')}\n"
            f"🕒 {data.get('time', '-')}\n\n"
        )
    bot.send_message(message.chat.id, text)

# 🔹 запуск
print("✅ Бот запущен и ожидает сообщений...")
bot.polling(none_stop=True)
