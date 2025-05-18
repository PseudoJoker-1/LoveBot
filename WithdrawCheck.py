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


API_TOKEN = ''

bot = telebot.TeleBot(API_TOKEN)

withdraws_id = []
withdraw_messages = {}
def send_notification():
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    
    # Получаем новые данные из базы данных
    cursor.execute('SELECT * FROM WithdrawRequests')
    new_withdraw = cursor.fetchall()

    if new_withdraw:
        for withdraw in new_withdraw:
            id, Withdrawamount, requesites, withdrawmethod, = withdraw[0], withdraw[1], withdraw[2], withdraw[3]
            
            if id not in withdraws_id:
                inlinekeyboard = types.InlineKeyboardMarkup(row_width=1)
                btn1 = types.InlineKeyboardButton(text="✅Завершено", callback_data=f'btn1_{id}')
                btn2 = types.InlineKeyboardButton(text="❌Игнорировать", callback_data=f'btn2_{id}')
                inlinekeyboard.add(btn1, btn2)
                
                message = f"🎉 Новые данные в таблице WithdrawsRequests:\n\n"
                message += f"👤 ID: {id}\nСумма: {Withdrawamount}\nРеквизиты: {requesites}\nМетод вывода: {withdrawmethod}\n"  
                
                global msg
                msg = bot.send_message(chat_id=734791656,text=message, reply_markup=inlinekeyboard)
                withdraw_messages[id] = message.message_id
                withdraws_id.append(id)
    
@bot.callback_query_handler(func=lambda callback: callback.data.startswith(('btn1_', 'btn2_')))
def denyoraccept(callback):
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor() 
    parts = callback.data.split('_')

    action = parts[0]
    userid = parts[1]
    if action == 'btn1':
        bot.delete_message(734791656,withdraw_messages[int(userid)])
        cursor.execute(f'DELETE FROM WithdrawRequests WHERE userid = {userid}')
        conn.commit()
    if action == 'btn2':
        bot.delete_message(734791656,withdraw_messages[int(userid)])
        cursor.execute(f'DELETE FROM WithdrawRequests WHERE userid = {userid}')
        conn.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(send_notification, 'interval', seconds=2, id='my_job_id')
scheduler.start()

bot.polling(none_stop=True)
