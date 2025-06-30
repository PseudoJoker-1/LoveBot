import telebot
from telebot import types
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler

API_TOKEN = '6469928294:AAGzW4kMdKFIaESa5fFG-enomZkd9SwUeOk'

bot = telebot.TeleBot(API_TOKEN)

conn = sqlite3.connect('db.db', check_same_thread=False)
cursor = conn.cursor()

sent_tickets = set()
ticket_messages = {}
active_chats = {}

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
            cursor.execute('SELECT id FROM Supports')
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
    ticket_id = call.data[len('accept_'):]
    print(ticket_id)
    cursor.execute('SELECT isActive FROM Tickets WHERE ticketid = ?', (ticket_id,))
    ticket = cursor.fetchone()

    if ticket and ticket[0] == "True":
        cursor.execute('UPDATE Tickets SET isActive = "False" WHERE ticketid = ?', (ticket_id,))
        conn.commit()
        bot.delete_message(call.message.chat.id, ticket_messages[ticket_id])

        support_id = call.message.chat.id
        user_id = int(ticket_id.split('_')[0])

        active_chats[ticket_id] = (support_id, user_id)

        bot.send_message(support_id, f"Вы начали общение с пользователем {user_id}")
        bot.send_message(user_id, "Оператор поддержки подключился к вашему тикету.")

        end_markup = types.InlineKeyboardMarkup()
        end_markup.add(types.InlineKeyboardButton("❌ Завершить диалог", callback_data=f'request_end_{ticket_id}'))

        bot.send_message(support_id, "Вы можете завершить диалог:", reply_markup=end_markup)
        bot.send_message(user_id, "Вы можете завершить диалог:", reply_markup=end_markup)

    else:
        bot.send_message(call.message.chat.id, 'Этим тикетом уже занимаются!')





@bot.message_handler(func=lambda msg: True)
def handle_chat(msg):
    for ticket_id, (support_id, user_id) in active_chats.items():
        if msg.chat.id == support_id:
            bot.send_message(user_id, f"💬 Поддержка: {msg.text}")
            return
        elif msg.chat.id == user_id:
            bot.send_message(support_id, f"👤 Пользователь: {msg.text}")
            return

@bot.callback_query_handler(func=lambda call: call.data.startswith('request_end_'))
def confirm_end_chat(call):
    ticket_id = call.data[len('request_end_'):]
    confirm_markup = types.InlineKeyboardMarkup()
    confirm_markup.add(
        types.InlineKeyboardButton("✅ Да, завершить", callback_data=f'confirm_end_{ticket_id}'),
        types.InlineKeyboardButton("❌ Отмена", callback_data='cancel')
    )
    bot.send_message(call.message.chat.id, "Вы уверены, что хотите завершить диалог?", reply_markup=confirm_markup)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel_end(call):
    bot.send_message(call.message.chat.id, "Завершение диалога отменено.")



@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_end_'))
def end_chat_confirmed(call):
    ticket_id = call.data[len('confirm_end_'):]
    chat = active_chats.get(ticket_id)

    if chat:
        support_id, user_id = chat

        bot.send_message(support_id, "Диалог завершён.")
        bot.send_message(user_id, "Диалог завершён. Спасибо за обращение!")

        # Удаляем тикет из базы
        cursor.execute('DELETE FROM Tickets WHERE ticketid = ?', (ticket_id,))
        conn.commit()

        del active_chats[ticket_id]
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔎Создать заявку"))
        bot.send_message(user_id, "Вы можете создать новую заявку:", reply_markup=markup)

        bot.register_next_step_handler_by_chat_id(user_id, create_ticket)
    else:
        bot.send_message(call.message.chat.id, "Этот диалог уже завершён.")



scheduler = BackgroundScheduler()
scheduler.add_job(check_new_tickets, 'interval', seconds=2)
scheduler.start()

bot.polling(none_stop=True)