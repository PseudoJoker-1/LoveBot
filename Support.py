import telebot
from telebot import types
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler

API_TOKEN = ''

bot = telebot.TeleBot(API_TOKEN)

conn = sqlite3.connect('db.db', check_same_thread=False)
cursor = conn.cursor()

sent_tickets = set()
ticket_messages = {}

# Проверка наличия профиля пользователя
def checkRealProfile(user_id):
    cursor.execute("SELECT id FROM Profiles WHERE id = ?", (user_id,))
    return cursor.fetchone() is not None

# Стартовая команда
@bot.message_handler(commands=['start'])
def start(message):
    if checkRealProfile(message.from_user.id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔎Создать заявку"))
        bot.send_message(message.chat.id, 'Приветствую тебя в поддержке LoveBot!', reply_markup=markup)
        bot.register_next_step_handler(message, create_ticket)
    else:
        bot.send_message(message.chat.id, 'У вас нет профиля!')

# Выбор типа тикета
def create_ticket(message):
    inlinekeyboard = types.InlineKeyboardMarkup(row_width=1)
    inlinekeyboard.add(
        types.InlineKeyboardButton("⚠️Баг, ошибка", callback_data='bug'),
        types.InlineKeyboardButton("❓Вопрос по боту", callback_data='question'),
        types.InlineKeyboardButton("💬Другое", callback_data='other')
    )
    bot.send_message(message.chat.id, 'Выберите тему для тикета', reply_markup=inlinekeyboard)

# Обработка типа тикета
@bot.callback_query_handler(func=lambda call: call.data in ('bug', 'question', 'other'))
def ticket_type_callback(call):
    bot.send_message(call.message.chat.id, 'Опишите подробно вашу проблему:')
    bot.register_next_step_handler(call.message, lambda msg: save_ticket(call.data, msg))

# Сохранение тикета
def save_ticket(ticket_type, message):
    user_id = message.from_user.id
    cursor.execute('SELECT userid FROM Tickets WHERE userid = ? AND isActive = "True"', (user_id,))
    if cursor.fetchone():
        bot.send_message(message.chat.id, 'У вас уже есть активная заявка.')
        return

    ticket_id = f"{user_id}_{message.message_id}"
    cursor.execute(
        'INSERT INTO Tickets (userid, ticketid, tickettype, ticketquestion, isActive) VALUES (?, ?, ?, ?, ?)',
        (user_id, ticket_id, ticket_type, message.text, "True")
    )
    conn.commit()
    bot.send_message(message.chat.id, 'Заявка успешно создана!')

def check_new_tickets():
    cursor.execute('SELECT userid, ticketid, tickettype, ticketquestion FROM Tickets WHERE isActive = "True"')
    new_tickets = cursor.fetchall()

    for ticket in new_tickets:
        user_id, ticket_id, ticket_type, question = ticket
        if ticket_id not in sent_tickets:
            cursor.execute('SELECT support_id FROM Supports')
            supports = cursor.fetchall()

            inlinekeyboard = types.InlineKeyboardMarkup(row_width=1)
            inlinekeyboard.add(types.InlineKeyboardButton("✅Принять", callback_data=f'accept_{ticket_id}'))

            for support in supports:
                msg = bot.send_message(support[0],
                                       f"Новый тикет\nАйди Тикета: {ticket_id}\nПользователь: {user_id}\nТип: {ticket_type}\nВопрос: {question}",
                                       reply_markup=inlinekeyboard)
                ticket_messages[ticket_id] = msg.message_id

            sent_tickets.add(ticket_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_'))
def accept_ticket(call):
    ticket_id = call.data.split('_')[1]
    cursor.execute('SELECT isActive FROM Tickets WHERE ticketid = ?', (ticket_id,))
    ticket = cursor.fetchone()

    if ticket and ticket[0] == "True":
        cursor.execute('UPDATE Tickets SET isActive = "False" WHERE ticketid = ?', (ticket_id,))
        conn.commit()
        bot.delete_message(call.message.chat.id, ticket_messages[ticket_id])
        user_id = ticket_id.split('_')[0]
        bot.send_message(call.message.chat.id, f"Вы начали общение с пользователем {user_id}")
        bot.register_next_step_handler(call.message, lambda msg: respond_to_user(msg, user_id))
    else:
        bot.send_message(call.message.chat.id, 'Этим тикетом уже занимаются!')


def respond_to_user(message, user_id):
    bot.send_message(user_id, message.text)
    bot.register_next_step_handler(message, lambda msg: respond_to_user(msg, user_id))


scheduler = BackgroundScheduler()
scheduler.add_job(check_new_tickets, 'interval', seconds=2)
scheduler.start()

bot.polling(none_stop=True)
