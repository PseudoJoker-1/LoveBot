
import sqlite3  # Для работы с базой данных SQLite
from xml.dom.domreg import registered  # Не используется, можно удалить
import telebot  # Для управления Telegram-ботом (библиотека pyTelegramBotAPI)
from telegram import Update  # Из другой библиотеки (python-telegram-bot), конфликтует с telebot
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler  # Конфликт, не используется
from apscheduler.schedulers.background import BackgroundScheduler  # Для запуска задач по расписанию
from apscheduler.triggers.interval import IntervalTrigger  # Интервальный триггер (не используется здесь)
from telebot import types  # Для создания клавиатур и кнопок
import base64  # Для декодирования аватара (фото) из строки
from io import BytesIO  # Для работы с байтовыми потоками (не используется)

# Токен для Telegram бота (замени перед публикацией)
API_TOKEN = '6827159024:AAFAN5mHflNXozDm8SIW5ZEwWecrSkK1XsA'

# Создание объекта бота
bot = telebot.TeleBot(API_TOKEN)

# Хранение ID уже отправленных профилей, чтобы не повторять
sent_profiles = []

# Хранение ID сообщений, чтобы потом их удалить
profile_messages = {}

# Функция для отправки уведомлений о новых профилях
def send_notification():
    conn = sqlite3.connect('db.db')  # Открытие соединения с базой данных
    cursor = conn.cursor()  # Получение курсора для выполнения SQL-запросов

    # Получаем все новые анкеты из таблицы NewProfiles
    Cursor1 = conn.execute('SELECT * FROM NewProfiles')
    new_profiles = Cursor1.fetchall()

    if new_profiles:
        for profile in new_profiles:
            # Распаковка значений из строки профиля
            id, Имя, Возраст, Хобби, Город, Пол, Аватар = profile[0], profile[1], profile[2], profile[3], profile[4], profile[6], profile[7]

            if id not in sent_profiles:  # Проверка, не отправляли ли уже этот профиль
                # Создание клавиатуры с кнопками
                inlinekeyboard = types.InlineKeyboardMarkup(row_width=1)
                btn1 = types.InlineKeyboardButton(text="✅Одобрить", callback_data=f'btn1_{id}')
                btn2 = types.InlineKeyboardButton(text="❌Отказать", callback_data=f'btn2_{id}')
                inlinekeyboard.add(btn1, btn2)

                # Формирование текста сообщения
                message = f"🎉 Новые данные в таблице NewProfiles:\n\n"
                message += f"👤 ID: {id}\nИмя: {Имя}\nВозраст: {Возраст}\nХобби: {Хобби}\nГород: {Город}\n Пол: {Пол}\n"

                # Сохраняем текущего пользователя глобально (чтобы потом использовать)
                global registered_user
                registered_user = (id, Имя, Возраст, Хобби, Город, Пол, Аватар)

                # Отправка фото с анкетой и кнопками
                global msg
                msg = bot.send_photo(chat_id=5202085137, photo=base64.b64decode(Аватар), caption=message, reply_markup=inlinekeyboard)

                # Сохраняем ID сообщения и добавляем ID в список отправленных
                profile_messages[id] = msg.message_id
                sent_profiles.append(id)

# Обработка нажатия кнопок ✅ и ❌
@bot.callback_query_handler(func=lambda callback: callback.data.startswith(('btn1_', 'btn2_')))
def denyoraccept(callback):
    conn = sqlite3.connect('db.db')  # Подключаемся к базе данных
    cursor = conn.cursor()

    parts = callback.data.split('_')  # Разделяем на действие и ID профиля
    action = parts[0]
    profile_id = parts[1]

    if action == 'btn1':
        # Удаляем сообщение
        bot.delete_message(734791656, profile_messages[int(profile_id)])

        # Переносим одобренный профиль в таблицу Profiles
        cursor.execute('INSERT INTO Profiles (id, Name, Age, Hobby, City, Sex, Image) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (profile_id, registered_user[1], registered_user[2], registered_user[3], registered_user[4], registered_user[5], registered_user[6]))
        conn.commit()

        # Удаляем анкету из NewProfiles
        cursor.execute(f"DELETE FROM NewProfiles WHERE id = {profile_id}")
        conn.commit()

        # Отправляем сообщение об успехе
        bot.send_message(chat_id=734791656, text="Удачно!")

    if action == 'btn2':
        # Удаляем сообщение с анкетой
        bot.delete_message(734791656, profile_messages[int(profile_id)])

        # Запрашиваем причину отказа
        bot.send_message(chat_id=734791656, text="Введите причину отказа")

        # Регистрируем обработчик следующего сообщения
        bot.register_next_step_handler_by_chat_id(chat_id=734791656, callback=process_denial_reason, profile_id=profile_id)

# Функция, обрабатывающая введённую причину отказа
def process_denial_reason(message, **kwargs):
    conn = sqlite3.connect('db.db')  # Подключение к базе
    cursor = conn.cursor()

    profile_id = kwargs.get('profile_id')  # Получаем ID профиля
    denial_reason = message.text  # Причина отказа

    # Обновляем причину отказа в таблице
    cursor.execute('UPDATE NewProfiles SET DenyMessage = ? WHERE id = ?', (denial_reason, profile_id))
    conn.commit()

    # Сообщаем об успехе
    bot.send_message(chat_id=734791656, text="Успешно добавлено: {}".format(denial_reason))

# Планировщик задач для периодической проверки базы
scheduler = BackgroundScheduler()
scheduler.add_job(send_notification, 'interval', seconds=2, id='my_job_id')  # Каждые 2 секунды проверяет новые анкеты
scheduler.start()  # Запускаем планировщик

# Запуск бота (постоянный опрос сервера Telegram)
bot.polling(none_stop=True)
