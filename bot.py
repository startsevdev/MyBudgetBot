# StartsevDev's MyBudgetBot


import sys
import sqlite3
import telebot
from telebot import types
from datetime import datetime
sys.path.append("../")
import tokens

print("\n- - - StartsevDev's MyBudgetBot - - -\n")

bot = telebot.TeleBot(tokens.MyBudgetBot)

WAIT_SIGN = 0
WAIT_SUM = 1
WAIT_CATEGORY = 2

output_categories = ["Гигиена", "Еда", "Жилье", "Здоровье", "Кафе", "Машина", "Одежда", "Питомцы",
                     "Подарки", "Отдых", "Связь", "Спорт", "Счета", "Такси", "Транспорт"]

input_categories = ["Депозиты", "Зарплата", "Сбережения"]


# SUPPORT FUNCTIONS

def console_print(message):
    now = datetime.strftime(datetime.now(), "%d.%m.%Y %H:%M:%S")
    print("{} | {}: {}".format(now, message.from_user.first_name, message.text))


def return_name(message):
    if message.from_user.last_name:
        name = message.from_user.last_name
    else:
        name = message.from_user.first_name

    return name


def return_state(message):
    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT state FROM users WHERE chat_id = {}".format(message.chat.id))
    state = cursor.fetchone()

    try:
        state = state[0]
    except TypeError as err:
        print("TypeError: ", err)
        bot.send_message(message.chat.id, "🔴 Ошибка. Чтобы начать работу, отправьте /start")
    else:
        return state

    conn.close()


def return_balance(result):
    balance = 0
    for tple in result:
        for i in tple:
            balance += i

    return balance


# ADD AND UPDATE DATA FUNCTIONS:


def set_state(message, state):
    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET state = {} WHERE chat_id = {}".format(state, message.chat.id))
    conn.commit()
    conn.close()


def add_user(message):
    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO users VALUES ({}, 0, Null, Null)".format(message.chat.id))
    except sqlite3.IntegrityError as err:
        print("sqlite3.IntegrityError: ", err)
        cursor.execute("UPDATE users SET state = 0, sign = NULL, sum = NULL WHERE chat_id = {}".format(message.chat.id))
        cursor.execute("DELETE FROM transactions WHERE chat_id = {}". format(message.chat.id))

    conn.commit()
    conn.close()


def update_sign(message):
    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE users
            SET sign = "{}", state = 1
            WHERE chat_id = {}'''.format(message.text, message.chat.id))
    except sqlite3.DatabaseError as err:
        print("Error: ", err)
        bot.send_message(message.chat.id, "🔴 Ошибка")
    else:
        conn.commit()
        remove_keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Введите сумму", reply_markup=remove_keyboard)

    conn.close()


def update_sum(message):
    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
        UPDATE users
        SET sum = {}, state = 2
        WHERE chat_id = {}'''.format(message.text, message.chat.id))
    except sqlite3.DatabaseError as err:
        print("Error: ", err)
        bot.send_message(message.chat.id, "🔴 Ошибка")
    else:
        conn.commit()

        cursor.execute("SELECT sign from users WHERE chat_id = {}".format(message.chat.id))
        sign = cursor.fetchone()[0]
        if sign == "-":
            output_categories_keyboard(message)
        else:
            input_categories_keyboard(message)

    conn.close()


def add_transaction(message):
    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT sign FROM users WHERE chat_id = {}". format(message.chat.id))
        sign = cursor.fetchone()[0]
        cursor.execute("SELECT sum FROM users WHERE chat_id = {}".format(message.chat.id))
        sum = cursor.fetchone()[0]
        pay = int(sign + str(sum))
        category = message.text
        date = datetime.strftime(datetime.now(), "%Y-%m-%d")
        cursor.execute("INSERT INTO transactions VALUES (NULL, {}, {}, '{}', '{}')".format(message.chat.id, pay, category, date))
        cursor.execute("UPDATE users SET state = 0, sign = NULL, sum = NULL WHERE chat_id = {}".format(message.chat.id))
    except sqlite3.DatabaseError as err:
        print("Error: ", err)
        bot.send_message(message.chat.id, "🔴 Ошибка")
    else:
        bot.send_message(message.chat.id, "Запись добавлена!")
        signs_keyboard(message, "Введите знак: ")

        conn.commit()

    conn.close()


def cancel_transaction(message):
    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET state = 0, sign = NULL, sum = NULL WHERE chat_id = {}".format(message.chat.id))
    conn.commit()
    conn.close()


# DISPLAY DATA FUNCTIONS

def stat_day(message):
    date = datetime.strftime(datetime.now(), '%Y-%m-%d')
    categories_dict = {}
    msg = ""

    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()

    for category in output_categories:
        cursor.execute('''
        SELECT sum
        FROM transactions 
        WHERE chat_id = {} AND date = "{}" AND category = "{}"'''.format(message.chat.id, date, category))
        result = cursor.fetchone()
        if result == None:
            categories_dict[category] = 0
        else:
            categories_dict[category] = result[0]

        msg += "{}: {}\n".format(category, categories_dict[category])
    conn.close()

    bot.send_message(message.chat.id, msg)
    cancel_transaction(message)
    signs_keyboard(message, "Введите знак: ")


def stat_week(message):
    now = datetime.strftime(datetime.now(), '%Y-%m-%d')

    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT sum
    FROM transactions 
    WHERE chat_id = {} AND strftime('%W%Y', date) = strftime('%W%Y', "{}")'''.format(message.chat.id, now))
    result = cursor.fetchall()
    conn.close()

    bot.send_message(message.chat.id, "Баланс за неделю: {}".format(return_balance(result)))
    cancel_transaction(message)
    signs_keyboard(message, "Введите знак: ")


def stat_month(message):
    now = datetime.strftime(datetime.now(), '%Y-%m-%d')

    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT sum
    FROM transactions 
    WHERE chat_id = {} AND strftime('%Y-%m', date) = strftime('%Y-%m', "{}")'''.format(message.chat.id, now))
    result = cursor.fetchall()
    conn.close()

    bot.send_message(message.chat.id, "Баланс за месяц: {}".format(return_balance(result)))
    cancel_transaction(message)
    signs_keyboard(message, "Введите знак: ")


def stat_year(message):
    now = datetime.strftime(datetime.now(), '%Y-%m-%d')

    conn = sqlite3.connect('mbb_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT sum
    FROM transactions 
    WHERE chat_id = {} AND strftime('%Y', date) = strftime('%Y', "{}")'''.format(message.chat.id, now))
    result = cursor.fetchall()
    conn.close()

    bot.send_message(message.chat.id, "Баланс за год: {}".format(return_balance(result)))
    cancel_transaction(message)
    signs_keyboard(message, "Введите знак: ")


# KEYBOARDS:

def signs_keyboard(message, keyboard_message):
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    keyboard.add("+")
    keyboard.add("-")

    bot.send_message(message.chat.id, keyboard_message, reply_markup=keyboard)


def input_categories_keyboard(message):
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for category in input_categories:
        keyboard.add(category)

    bot.send_message(message.chat.id, "Выберите категорию: ", reply_markup=keyboard)


def output_categories_keyboard(message):
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)

    rows = []
    for i in range(0, len(output_categories), 3):
        rows.append(output_categories[i: i + 3])
    for row in rows:
        keyboard.row(row[0], row[1], row[2])

    bot.send_message(message.chat.id, "Выберите категорию: ", reply_markup=keyboard)


# HANDLERS

@bot.message_handler(commands=['test'])
def test(message):
    keyboard = types.ReplyKeyboardMarkup()
    for row in output_categories:
        keyboard.row(row[0], row[1], row[2], row[3], row[4])

    bot.send_message(message.chat.id, "Выберите категорию: ", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "-":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Минус")
    elif call.data == "+":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Минус")


@bot.message_handler(commands=['start'])
def start(message):
    console_print(message)

    add_user(message)

    bot.send_message(message.chat.id, "Добро пожаловать, {}!".format(return_name(message)))
    signs_keyboard(message, "Введите знак: ")


@bot.message_handler(commands=['help'])
def help(message):
    console_print(message)

    help_msg = '''
    Команды для управления ботом:
    
    /cancel - Отменить ввод
    
    /day — Статистика за день
    
    /week — Статистика за неделю
    
    /month — Статистика за месяц
    
    /year — Статистика за год
    
    /help — Список всех комманд
    '''

    bot.send_message(message.chat.id, help_msg)


@bot.message_handler(commands=['day'])
def day(message):
    console_print(message)
    stat_day(message)


@bot.message_handler(commands=['week'])
def week(message):
    console_print(message)
    stat_week(message)


@bot.message_handler(commands=['month'])
def month(message):
    console_print(message)
    stat_month(message)


@bot.message_handler(commands=['year'])
def year(message):
    console_print(message)
    stat_year(message)


@bot.message_handler(commands=['cancel'])
def cancel(message):
    console_print(message)
    cancel_transaction(message)
    signs_keyboard(message, "Ввод отменен. Введите знак: ")


@bot.message_handler()
def giving_text(message):
    console_print(message)

    if return_state(message) == 0:
        if message.text == "-" or message.text == "+":
            update_sign(message)
        else:
            bot.send_message(message.chat.id, "🔴 Ошибка. Введите знак")
    elif return_state(message) == 1:
        if message.text.isdigit() and len(message.text) <= 18:
            update_sum(message)
        else:
            bot.send_message(message.chat.id, "🔴 Ошибка. Введите сумму")
    elif return_state(message) == 2:
        add_transaction(message)
    else:
        bot.send_message(message.chat.id, "🔴 Ошибка. Выберите категорию")


bot.polling(none_stop=0, interval=0)
