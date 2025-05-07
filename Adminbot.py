import sqlite3
from xml.dom.domreg import registered
import telebot
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telebot import types
from telegram.ext import Updater
from telegram.ext import CallbackQueryHandler
import base64
from io import BytesIO

API_TOKEN = '6827159024:AAFAN5mHflNXozDm8SIW5ZEwWecrSkK1XsA'

bot = telebot.TeleBot(API_TOKEN)

sent_profiles = []
profile_messages = {}

def send_notification():
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    
    # Получаем новые данные из базы данных
    Cursor1 = conn.execute('SELECT * FROM NewProfiles')
    new_profiles = Cursor1.fetchall()

    if new_profiles:
        for profile in new_profiles:
            id, Имя, Возраст, Хобби, Город, Пол, Аватар = profile[0], profile[1], profile[2], profile[3], profile[4], profile[6], profile[7]
            
            if id not in sent_profiles:
                inlinekeyboard = types.InlineKeyboardMarkup(row_width=1)
                btn1 = types.InlineKeyboardButton(text="✅Одобрить", callback_data=f'btn1_{id}')
                btn2 = types.InlineKeyboardButton(text="❌Отказать", callback_data=f'btn2_{id}')
                inlinekeyboard.add(btn1, btn2)
                
                message = f"🎉 Новые данные в таблице NewProfiles:\n\n"
                message += f"👤 ID: {id}\nИмя: {Имя}\nВозраст: {Возраст}\nХобби: {Хобби}\nГород: {Город}\n Пол: {Пол}\n"  
                global registered_user
                registered_user = (id, Имя, Возраст, Хобби, Город,Пол,Аватар) 



                global msg
                msg = bot.send_photo(chat_id=734791656,photo=base64.b64decode(Аватар), caption=message, reply_markup=inlinekeyboard)
                profile_messages[id] = msg.message_id
                sent_profiles.append(id)

@bot.callback_query_handler(func=lambda callback: callback.data.startswith(('btn1_', 'btn2_')))
def denyoraccept(callback):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor() 

    parts = callback.data.split('_')
    action = parts[0]
    profile_id = parts[1]

    if action == 'btn1':
        bot.delete_message(734791656,profile_messages[int(profile_id)])
        cursor.execute('INSERT INTO Profiles (id, Name, Age, Hobby, City, Sex,Image) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (profile_id, registered_user[1], registered_user[2], registered_user[3], registered_user[4],registered_user[5], registered_user[6]))
        conn.commit()

        cursor.execute(f"DELETE FROM NewProfiles WHERE id = {profile_id}")
        conn.commit()
        bot.send_message(chat_id=734791656, text="Удачно!")
    if action == 'btn2':
        bot.delete_message(734791656,profile_messages[int(profile_id)])
        bot.send_message(chat_id=734791656, text="Введите причину отказа")
        bot.register_next_step_handler_by_chat_id(chat_id=734791656, callback=process_denial_reason, profile_id=profile_id)
    

def process_denial_reason(message, **kwargs):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()

    profile_id = kwargs.get('profile_id')
    denial_reason = message.text

    cursor.execute('UPDATE NewProfiles SET DenyMessage = ? WHERE id = ?', (denial_reason, profile_id))
    conn.commit()

    bot.send_message(chat_id=734791656, text="Успешно добавлено: {}".format(denial_reason))
scheduler = BackgroundScheduler()
scheduler.add_job(send_notification, 'interval', seconds=2, id='my_job_id')
scheduler.start()

bot.polling(none_stop=True)
