import os
import database
from database import User, Cars
import re
import telebot
from telebot.types import MenuButtonCommands, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton

bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))


@bot.message_handler(commands=['start'])
def start(message):
    bot.set_my_commands(commands=[BotCommand(command='start', description='Запустить бот'),
                                  BotCommand(command='add_auto', description='Добавить мой автомобиль'),
                                  BotCommand(command='search_auto', description='Найти автомобиль'),
                                  BotCommand(command='my_auto', description='Мои автомобили')])
    bot.set_chat_menu_button(chat_id=message.chat.id, menu_button=MenuButtonCommands('commands'), )
    session = database.create_db_connection()()
    users = session.query(User.user_id).all()
    if message.from_user.id not in [ids[0] for ids in users]:
        session.add(User(user_id=message.from_user.id, status_id=1))
        session.commit()
        session.close()

        msg = bot.send_message(chat_id=message.chat.id, text='Добро пожаловать.\n'
                                                             'Для завершения регистрации пожалуйста '
                                                             'отправьте ваше ФИО.')
        bot.register_next_step_handler(message=msg, callback=fio_data)
    else:
        bot.send_message(chat_id=message.chat.id, text='Вы уже зарегистрированы в чате')


def fio_data(message):
    session = database.create_db_connection()()
    adding_fio = session.query(User).filter_by(user_id=message.from_user.id).first()
    adding_fio.fio = str(message.text)
    session.commit()
    session.close()

    bot.send_message(chat_id=message.chat.id, text='Регистрация завершена успешно')


@bot.message_handler(commands=['add_auto'])
def add_auto(message):
    msg = bot.send_message(chat_id=message.chat.id, text='Шаг 1 из 2.\n'
                                                         'Пожалуйста введите номер автомобиля в следующем порядке:\n'
                                                         '1. Четыре цифры (Латинская буква E и три цифры '
                                                         'для электромобилей)\n'
                                                         '2. Пробел\n'
                                                         '3. Две латинские буквы\n'
                                                         '4. Тире\n'
                                                         '5. Одна цифра (регион)\n'
                                                         'Пример: 1234 BB-7')
    bot.register_next_step_handler(message=msg, callback=provide_number)


def provide_number(message, old_data=''):
    if re.match(pattern=r'^[0-9E]\d{3} [ABEIKMHOPCTX]{2}-[1-7]$', string=str(message.text).upper()):
        msg = bot.send_message(chat_id=message.chat.id, text='Шаг 2 из 2\n'
                                                             'Введите марку автомобиля')
        bot.register_next_step_handler(message=msg,
                                       callback=provide_brand,
                                       car_number=str(message.text).upper(),
                                       old_data=old_data)
    else:
        msg = bot.send_message(chat_id=message.chat.id, text="Не удалось распознать номер. Попробуйте снова.")
        bot.register_next_step_handler(message=msg, callback=provide_number, old_data=old_data)


def provide_brand(message, car_number, old_data):
    session = database.create_db_connection()()
    if old_data == '':
        session.add(Cars(user_id=message.from_user.id, car_number=car_number, brand=str(message.text)))
        session.commit()
        bot.send_message(chat_id=message.chat.id, text='Автомобиль успешно добавлен')
    else:
        filter_car = session.query(Cars).filter_by(id=old_data).first()
        filter_car.car_number = car_number
        filter_car.brand = str(message.text)
        session.commit()
        bot.send_message(chat_id=message.chat.id, text='Данные автомобиля изменены')
    session.close()


@bot.message_handler(commands=['search_auto'])
def search_auto(message):
    msg = bot.send_message(chat_id=message.chat.id, text='Введите номер автомобиля для поиска')
    bot.register_next_step_handler(message=msg, callback=search_result)


def search_result(message):
    session = database.create_db_connection()()
    result = session.query(Cars).filter_by(car_number=str(message.text).upper()).join(User).filter_by(status_id=1).all()

    if len(result) > 0:
        bot.send_message(chat_id=message.chat.id, text=f'Найденых записей: {len(result)}')
        for el in result:
            inline_keyboard = InlineKeyboardMarkup(row_width=1)
            inline_keyboard.add(InlineKeyboardButton(text='Отправить сообщение о блокировке',
                                                     callback_data=','.join([str(el.user_id), el.car_number])))
            bot.send_message(chat_id=message.chat.id, text=f'Автомобиль: {el.brand}\n'
                                                           f'Владелец: {el.user.fio}', reply_markup=inline_keyboard)
    else:
        bot.send_message(chat_id=message.chat.id, text='Автомобилей с указанным номером не найдено')
    session.close()


@bot.callback_query_handler(
    func=lambda message: message.message.reply_markup.keyboard[0][0].text == 'Отправить сообщение о блокировке')
def send_block_auto_message(message):
    bot.send_message(chat_id=message.data.split(',')[0],
                     text=f'Ваш автомобиль с регистрационным номером {message.data.split(",")[1]} блокирует выезд')
    bot.answer_callback_query(callback_query_id=message.id, text='Пользователь уведомлен')


@bot.message_handler(commands=['my_auto'])
def search_result(message):
    session = database.create_db_connection()()
    result = session.query(Cars).filter_by(user_id=message.chat.id).all()
    if len(result) > 0:
        bot.send_message(chat_id=message.chat.id, text=f'Найденых автомобилей: {len(result)}')
        for el in result:
            inline_keyboard = InlineKeyboardMarkup(row_width=2)
            inline_keyboard.add(InlineKeyboardButton(text='Изменить', callback_data=f'chan_{el.id}'),
                                InlineKeyboardButton(text='Удалить', callback_data=f'del_{el.id}'))
            bot.send_message(chat_id=message.chat.id, text=f'Автомобиль: {el.brand}\n'
                                                           f'Номер: {el.car_number}', reply_markup=inline_keyboard)
    else:
        bot.send_message(chat_id=message.chat.id, text='Автомобилей не найдено')
    session.close()


@bot.callback_query_handler(func=lambda message: message.message.reply_markup.keyboard[0][0].text == 'Изменить')
def change_car_data(message):
    if 'chan' in message.data:
        msg = bot.send_message(chat_id=message.from_user.id, text='Шаг 1 из 2.\n'
                                                                  'Пожалуйста введите номер автомобиля в следующем порядке:\n'
                                                                  '1. Четыре цифры (Латинская буква E и три цифры '
                                                                  'для электромобилей)\n'
                                                                  '2. Пробел\n'
                                                                  '3. Две латинские буквы\n'
                                                                  '4. Тире\n'
                                                                  '5. Одна цифра (регион)\n'
                                                                  'Пример: 1234 BB-7')
        bot.register_next_step_handler(message=msg, callback=provide_number, old_data=message.data[5:])
    elif 'del' in message.data:
        session = database.create_db_connection()()
        select_car = session.query(Cars).filter_by(id=message.data[4:]).first()
        session.delete(select_car)
        session.commit()
        session.close()
        bot.send_message(chat_id=message.from_user.id, text='Автомобиль удалён')


if __name__ == '__main__':
    bot.polling()
