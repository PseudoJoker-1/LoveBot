import telebot
from telebot import types
import re
import sqlite3
from telebot.types import ReplyKeyboardRemove
import random
from pathlib import Path
import base64
import time


conn = sqlite3.connect('db.db', check_same_thread=False)
cursor = conn.cursor()

API_TOKEN = '6405524079:AAGu7AeTYChxVGm_zsBlzXbUZ8XMTTMksO8'
PAYMENTS_TOKEN = '5420394252:TEST:543267'

bot = telebot.TeleBot(API_TOKEN)


alreadyfindedprofiles = []




def checkRealProfile(userIdent):
    Cursor2 = conn.execute(f"SELECT id FROM Profiles")
    result2 = [row[0] for row in Cursor2.fetchall()]
    for i in result2:
        if str(i) == str(userIdent):
            return True
    return False

def checkProfile(userId):
    Cursor1 = conn.execute(f"SELECT * FROM NewProfiles")
    result1 = Cursor1.fetchall()
    for i in result1:
        if i[0] == userId:
            return True
    return False




def db_table_val(id, Name, Age, Hobby,City,Sex,Image):
    cursor.execute('INSERT INTO NewProfiles (id, Name, Age, Hobby,City,Sex,Image) VALUES (?, ?, ?, ?, ?, ?, ?)', (id, Name, Age, Hobby,City,Sex,Image))
    conn.commit()
def проверить_формат(пользовательский_ввод):

    # Регулярные выражения для проверки формата
    имя_регулярка = re.compile(r"^[А-Яа-яA-Za-z\s]+$")
    возраст_регулярка = re.compile(r"^\d+$")
    хобби_регулярка = re.compile(r"^[А-Яа-яA-Za-z\s,]+$")
    город_регулярка = re.compile(r"^[А-Яа-яA-Za-z\s]+$")
    пол_регулярка = re.compile(r"^[А-Яа-яA-Za-z\s]+$")

    # Проверка соответствия формату
    соответствует_имя = имя_регулярка.match(пользовательский_ввод[0].strip())
    соответствует_возраст = возраст_регулярка.match(пользовательский_ввод[1].strip())
    соответствует_хобби = хобби_регулярка.match(пользовательский_ввод[2].strip())
    соответствует_город = город_регулярка.match(пользовательский_ввод[3].strip())
    соответствует_пол = пол_регулярка.match(пользовательский_ввод[4].strip())
    

    return соответствует_имя and соответствует_возраст and соответствует_хобби and соответствует_город and соответствует_пол



#-----ПОПОЛНЕНИЕ БАЛАНСА-----#
def is_number(num):
    try:
        int(num)
        return True
    except ValueError:
        return False
@bot.message_handler(commands=['refill'])
def buy(message):
    if checkRealProfile(message.from_user.id):
        isgotpayment = False
        msg1 = bot.send_message(message.chat.id,'Напишите сумму на которую вы хотите пополнить баланс')
        bot.register_next_step_handler(message, balance)
    else:
        bot.send_message(message.chat.id,"У вас нет профиля!")


def balance(message):
    if is_number(message.text):
        global amountrefill
        amountrefill = message.text
        PRICE = types.LabeledPrice(label="Пополнение баланса", amount=int(amountrefill) * 100)
        global paymsg
        paymsg = bot.send_invoice(message.chat.id,
                        title="Пополнение личного баланса",
                        description=f"Пополнение на сумму {amountrefill}₸. Оплатите в течении 5 минут!",
                        provider_token=PAYMENTS_TOKEN,
                        currency="kzt",
                        is_flexible=False,
                        prices=[PRICE],
                        start_parameter="refill-balance",
                        invoice_payload="test-invoice-payload",

                        )
        time.sleep(300)
        if isgotpayment == False:
            bot.delete_message(message.chat.id,paymsg.message_id)
    else:
        bot.send_message(message.chat.id,'Не правильный формат!')
        bot.register_next_step_handler(message, balance)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                  error_message="Произошла ошибка попробуйте еще раз")


@bot.message_handler(content_types=['successful_payment'])
def gotpayment(message):
    global isgotpayment 
    isgotpayment = False
    isgotpayment = True
    bot.send_message(message.chat.id,f'✅Вы успешно пополни баланс на {amountrefill}')
    cursor.execute(f'UPDATE Profiles SET balance = ? WHERE id = ?', (amountrefill, message.from_user.id))
    conn.commit()
    bot.delete_message(message.chat.id,paymsg.message_id)


#------ПРОВЕРКА БАЛАНСА-------#
@bot.message_handler(commands=['mybalance'])
def my_balance(message):
    if checkRealProfile(message.from_user.id):
        request = conn.execute(f'SELECT balance FROM Profiles WHERE id = {message.from_user.id}')
        user_balance = request.fetchone()
        bot.send_message(message.chat.id,'💸Ваш текущий баланс составляет: ' + str(user_balance[0]))

    

#--------ОСНОВНОЙ БЛОК---------#
@bot.message_handler(commands=['start'])
def help_message(message):
    if checkRealProfile(message.from_user.id):
        user_id = message.from_user.id
        query = f"SELECT Name FROM Profiles WHERE id = {user_id}"
        UserName1 = conn.execute(query).fetchone()
        markup1 = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn2 = types.KeyboardButton("🔎Поиск пары")
        btn3 = types.KeyboardButton('💸Баланс')
        btn4 = types.KeyboardButton('🛠️Техническая поддержка')
        markup1.add(btn2,btn3,btn4)
        
        bot.send_message(message.chat.id,"Добро пожаловать обратно," + UserName1[0] + "😊\n\n"
                                      "Рады видеть вас снова! Если у вас есть какие-либо вопросы или вы хотите начать новый разговор, просто выберите из пункта. Удачи в общении!",reply_markup=markup1)
        bot.register_next_step_handler(message, searchForPair)
        
    elif checkProfile(message.from_user.id):
        id = message.from_user.id
        if checkDenialReason(id):
            bot.send_message(message.chat.id,"Ваш профиль был отказан модератором! Причина: " + reason)
            cursor.execute(f'DELETE FROM NewProfiles WHERE id = {id}')
            conn.commit()
        else:
            bot.send_message(message.chat.id, "Ваш профиль уже отправлян на модерацию ожидайте!",reply_markup=ReplyKeyboardRemove())
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Создать профиль")
        markup.add(btn1)
        bot.send_message(message.chat.id, """\
Привет! 👋 Добро пожаловать в бот для знакомства! Я здесь, чтобы помочь тебе найти новых интересных людей для общения. 😊

Для того чтобы начать знакомится нужно создать свой профиль🗣️

Не забывай, что здесь главное — удовольствие от общения! 🌟 Если у тебя есть вопросы или нужна помощь, просто напиши "Помощь". Удачи в знакомствах! 🚀
\
""", reply_markup=markup)
        bot.register_next_step_handler(message,stats_message)


def stats_message(message):
    if message.text == "Создать профиль":
        if checkProfile(message.from_user.id):      
            if checkDenialReason(message.from_user.id):
                bot.send_message("Ваш профиль был отказан модератором! Причина: " + reason)
                cursor.execute(f'DELETE FROM NewProfiles WHERE id = {message.from_user.id}')
                conn.commit()
            else:
                bot.send_message(message.chat.id,"Ваш профиль отправлен на модерацию ожидайте!")
        elif checkRealProfile(message.from_user.id):
            bot.send_message(message.chat.id,"У вас уже есть созданный профиль!")
        else: 
            bot.send_message(message.chat.id, """\
        Отлично! Давай создадим твой профиль. 🌟

Напиши, как тебя зовут и что-то интересное о себе. Можешь поделиться своими хобби, любимыми фильмами или музыкой. Также, укажи свой возраст, чтобы было легче найти подходящих собеседников.

    Пример:
    📌 Имя: Анна
    👤 Возраст: 25
    🎯 Хобби: Люблю читать книги и готовить вкусную еду. Обожаю путешествовать!
    🌇 Город: Астана
     ♂️ Пол: Женский                        

Не стесняйся быть творческим! Чем больше информации, тем легче найти единомышленников. Готово? Просто отправь свою информацию, и мы начнем поиск интересных собеседников для тебя. 🚀\
""", reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(message, handle_profile_data)

@bot.message_handler(content_types='text')
def searchForPair(message):
    if message.text == "🔎Поиск пары":
        if checkRealProfile(message.from_user.id):
            user_id = message.from_user.id  # Получаем id пользователя, который запросил поиск пары
            user_profile = get_user_profile(user_id)
        
            if user_profile:
            # Найдем подходящую пару для пользователя
                pair_profile = find_matching_pair(user_profile)
            
                if pair_profile:
                # Нашли подходящую пару
                    send_pair_info_with_buttons(message.chat.id,user_profile,pair_profile)
        else:
            bot.send_message(message.chat.id,'Вы еще не создали профиль либо ваш профиль находится на модерации!')
    elif message.text == "💸Баланс":
        if checkRealProfile(message.from_user.id):
            user_profile = get_user_profile(message.from_user.id)
            if user_profile[7] < 500:
                bot.send_message(message.chat.id,f'Ваш текущий баланс составляет: {user_profile[7]} KZT')
            elif user_profile[7] > 500:
                inlinekeyboard = types.InlineKeyboardMarkup(row_width=1)
                button1 = types.InlineKeyboardButton(text="Вывести деньги", callback_data='withdraw_money')
                inlinekeyboard.add(button1)
                bot.send_message(message.chat.id,f'Ваш текущий баланс составляет: {user_profile[7]} KZT',reply_markup=inlinekeyboard)
        else:
            bot.send_message(message.chat.id,'Вы еще не создали профиль либо ваш профиль находится на модерации!')
    elif message.text == '🛠️Техническая поддержка':
        bot.send_message(message.chat.id,'Для обращения в тех поддержку - @LoveSupportingBot')



def get_user_profile(user_id):
    # Функция для получения профиля пользователя из базы данных по его id
    Cursor123 = conn.execute('SELECT * FROM Profiles')
    for profile in Cursor123:
        if profile[0] == user_id:
            return profile
    return None

def find_matching_pair(user_profile):
    # Функция для поиска подходящей пары для пользователя
    # Здесь может быть ваш алгоритм поиска, основанный на интересах, возрасте и т. д.
    # В данном примере просто выбирается случайный профиль из базы данных.
    database = conn.execute("SELECT * FROM Profiles")
    try:
        other_profiles = [profile for profile in database if profile[0] != user_profile[0] and profile[5] != user_profile[5] and profile[4] == user_profile[4] and profile[0] not in alreadyfindedprofiles]
        return random.choice(other_profiles)
    except:
        return None
    

def send_pair_info_with_buttons(chat_id, user_profile, pair_profile):
    # Отправляем информацию о паре и инлайн-кнопки
    inlinekeyboard = types.InlineKeyboardMarkup(row_width=1)
    button1 = types.InlineKeyboardButton(text="➡️Найти следующую пару", callback_data='find_next_pair')
    button2 = types.InlineKeyboardButton(text="❤️", callback_data='like')
    button3 = types.InlineKeyboardButton(text="💳Пожертвовать денег", callback_data='send_money')
    inlinekeyboard.add(button1, button2,button3)


    message = '\nИмя: ' +  pair_profile[1] + '\nВозраст: ' + str(pair_profile[2]) + '\nХобби: ' + pair_profile[3] + '\nГород: ' + pair_profile[4] + '\nПол: ' + pair_profile[5]
    i = bot.send_photo(chat_id,photo=base64.b64decode(pair_profile[6]),caption=message,reply_markup=inlinekeyboard )
    global idmessage
    idmessage = i.message_id
    alreadyfindedprofiles.append(pair_profile[0])
    print(pair_profile[0])


@bot.callback_query_handler(func=lambda call: True)
def handle_button_click(callback):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    username = callback.from_user.username
    global profil
    global user_profile
    user_profile = get_user_profile(user_id)
    if callback.data == 'find_next_pair':  
        bot.delete_message(chat_id,idmessage)       
        if user_profile:
            # Найдем следующую подходящую пару для пользователя
            pair_profile = find_matching_pair(user_profile)
            
            if pair_profile and pair_profile[0] not in alreadyfindedprofiles:
                # Отправляем информацию о следующей паре и обновляем инлайн-кнопки
                send_pair_info_with_buttons(chat_id, user_profile, pair_profile)
            else:
                # Подходящая пара не найдена
                bot.send_message(chat_id,"Подходящая пара не найдена!")
        else:
            # Профиль пользователя не найден в базе данных
            bot.send_message(chat_id,'Профиль пользователя не найден!')

    elif callback.data == 'like':
        # Обработка нажатия кнопки "Лайк"
        # Отправляем уведомление пользователю, которому достался лайкfd
        inlinekeyboard123 = types.InlineKeyboardMarkup(row_width=1)
        button123 = types.InlineKeyboardButton(text="Посмотреть профиль", callback_data='review_profile')
        button234 = types.InlineKeyboardButton(text="Написать пользователю", url=f't.me/{username}')
        inlinekeyboard123.add(button123, button234)
        message = bot.send_message(alreadyfindedprofiles[-1], 'Вас лайкнул(а) пользователь показать его профиль?',reply_markup=inlinekeyboard123)
        global msg
        msg = message.message_id
    if callback.data == 'review_profile':
        bot.delete_message(alreadyfindedprofiles[-1],msg)
        user_profile_id = alreadyfindedprofiles[-1]  # ID пользователя, который лайкнул
        user_profile = get_user_profile(user_profile_id)  # Получение профиля пользователя из базы данных
    
        if user_profile:
            # Отправляем информацию о профиле пользователя
            inlinekeyboard1234 = types.InlineKeyboardMarkup(row_width=1)
            button1234 = types.InlineKeyboardButton(text="🤷Игнорировать", callback_data='ignore')
            button12345 = types.InlineKeyboardButton(text="🗨️Написать пользователю", url=f't.me/{username}')
            inlinekeyboard1234.add(button1234,button12345)
            profile_info = f"Имя: {user_profile[1]}\nВозраст: {user_profile[2]}\nХобби: {user_profile[3]}\nГород: {user_profile[4]}\nПол: {user_profile[5]}"
            profil = bot.send_photo(alreadyfindedprofiles[-1], base64.b64decode(user_profile[6]), profile_info,reply_markup=inlinekeyboard1234)
    if callback.data == 'ignore':

        bot.delete_message(chat_id,profil.message_id)
    if callback.data == 'send_money':
        bot.send_message(chat_id,'💳Введите желаемую сумму для перевода: ')
        bot.register_next_step_handler(callback.message,sendmoney)
        global pair_id
        global sendedmoney_user_profile
        sendedmoney_user_profile = get_user_profile(alreadyfindedprofiles[-1])
        pair_id = alreadyfindedprofiles[-1]
    if callback.data == 'withdraw_money':
        global WithdrawMethod
        bot.send_message(chat_id,'Введите сумму которую хотите вывести')
        bot.register_next_step_handler(callback.message,withdraw_money)
    if callback.data == 'Qiwi':
        WithdrawMethod = 'Qiwi'
        bot.send_message(chat_id,'Введите ваши реквизиты БЕЗ ПРОБЕЛОВ')
        bot.register_next_step_handler(callback.message,withdraw_process)
    if callback.data == 'BankCard':
        WithdrawMethod = 'BankCard'
        bot.send_message(chat_id,'Введите ваши реквизиты БЕЗ ПРОБЕЛОВ')
        bot.register_next_step_handler(callback.message,withdraw_process)
        
def withdraw_money(message):
    if is_number(message.text):
        global withdraw_amount
        withdraw_amount = message.text
        request = cursor.execute(f'SELECT balance FROM Profiles WHERE id = {message.chat.id}')
        checkBalance = request.fetchone()
        if int(message.text) == int(checkBalance[0]) or int(message.text) < int(checkBalance[0]):
            inlinekeyboard123 = types.InlineKeyboardMarkup(row_width=1)
            button123 = types.InlineKeyboardButton(text="Qiwi", callback_data='Qiwi')
            button234 = types.InlineKeyboardButton(text="Bank Cards", callback_data='BankCard')
            inlinekeyboard123.add(button123, button234)
            bot.send_message(message.chat.id,"Введите куда вы будете выводить деньги",reply_markup=inlinekeyboard123)
        else:
            bot.send_message(message.chat.id,'У вас недостаточный баланс пополните его!')
    else:
        bot.send_message(message.chat.id,'Не правильный формат! Введите число')
        bot.register_next_step_handler(message,withdraw_money)

def withdraw_process(message):
    if is_number(message.text):
        if len(message.text) == 1:
            bot.send_message(message.chat.id,"Неверный формат данных попробуйте убрать пробелы")
            bot.register_next_step_handler(message.chat.id,withdraw_money)
        else:
            cursor.execute('INSERT INTO WithdrawRequests (userid, WithdrawAmount, Requisites, WithdrawMethod) VALUES (?, ?, ?, ?)', (message.from_user.id,withdraw_amount,message.text,WithdrawMethod))
            conn.commit()
            bot.send_message(message.chat.id,'Вы успешно создали заявку на вывод денег ожидайте!')
    else:
        bot.send_message(message.chat.id,'Неверный формат данных')
        bot.register_next_step_handler(message,withdraw_process)



def sendmoney(message):
    if is_number(message.text):
        anotherquery = f'SELECT balance FROM Profiles WHERE id = {message.from_user.id}'
        userbalance = conn.execute(anotherquery)
        result = userbalance.fetchone()
        if result[0] < int(message.text):
            bot.send_message(message.chat.id,'У вас недостаточный баланс! Пополните его')
        else:
            result2 = result[0] - int(message.text)
            cursor.execute(f'UPDATE Profiles SET balance = ? WHERE id = ?',(message.text,pair_id))
            conn.commit()
            cursor.execute(f'UPDATE Profiles SET balance = ? WHERE id = ?',(result2,message.from_user.id))
            conn.commit()
            bot.send_message(message.chat.id,f'Вы успешно перевели {sendedmoney_user_profile[1]} {message.text} KZT!')
            bot.send_message(alreadyfindedprofiles[-1],f'Вам перевели {message.text} KZT от {user_profile[1]}')
    else:
        bot.send_message(message.chat.id,"Неверный формат данных. Введите еще раз")
        bot.register_next_step_handler(message,sendmoney)


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if canSendPhoto == True:
        bot.send_message(message.chat.id,'Ваш профиль отправлен на модерацию ожидайте!')
    # Получаем информацию о файле изображения
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
    
    # Скачиваем изображение
        downloaded_file = bot.download_file(file_path)
    
    # Сохраняем изображение в файл
        with open("user_photo.jpg", 'wb') as new_file:
            new_file.write(downloaded_file)
    

        photo_base64 = base64.b64encode(downloaded_file).decode('utf-8')

    # После сохранения изображения можно вызвать функцию handle_profile_data,
    # передав сохраненное изображение и message, чтобы извлечь текст профиля
        avatar(photo_base64)
   
def handle_profile_data(message):
    try:
        данные_профиля = [x.strip() for x in message.text.split(',')]
        if len(данные_профиля) != 5:
            raise ValueError("Неверный формат данных")
        имя = данные_профиля[0]
        возраст = данные_профиля[1]
        хобби = данные_профиля[2]
        город = данные_профиля[3]
        пол = данные_профиля[4]
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат данных. Пожалуйста, следуйте указанному формату.")
        bot.register_next_step_handler(message, handle_profile_data)
        return

   
    if not проверить_формат(данные_профиля):
        bot.send_message(message.chat.id, "Неверный формат данных. Пожалуйста, следуйте указанному формату.")
        bot.register_next_step_handler(message, handle_profile_data)
        return

    global us_id
    global us_name
    global age
    global hobby
    global city
    global sex
    us_id = message.from_user.id  
    us_name = данные_профиля[0]  
    age = данные_профиля[1]
    hobby = данные_профиля[2]
    city = данные_профиля[3]
    sex = данные_профиля[4]
    bot.send_message(message.chat.id, "Отправьте ваше фото: ",reply_markup=ReplyKeyboardRemove())
    global canSendPhoto
    canSendPhoto = True
    has_Profile = True

def avatar(img):
    db_table_val(id=us_id, Name=us_name, Age=age, Hobby=hobby,City=city, Sex=sex,Image=img)

def checkDenialReason(UserID):
    query = 'SELECT * FROM NewProfiles'
    Cursor = conn.execute(query)
    result = Cursor.fetchall()
    print(result[0])

    for i in result:
        if i[0] == UserID and i[5] != None:
            print("Ваш профиль был отказан модератором! Причина: " + i[5])
            global reason
            reason = i[5]
            return i[5]
    return False




bot.polling(none_stop=True)