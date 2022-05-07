import requests
import vk_api
from vk_api.longpoll import VkLongPoll

from string import ascii_lowercase, digits
from random import choice
from json import load

from data import db_session
from data.user import User
from data.admin_code import AdminCode
from data.redemption_code import RedemptionCode

config_file = 'config.json'  # Файл конфига
with open(config_file, mode='r', encoding='utf-8') as f:
    data = load(f)
    db = data['database']  # Файл с Базой Данных
    bot_token = data['bot_token']  # Токен Бота (чтение/ответ в ЛС Группы)
    app_token = data['app_token']  # Токен Приложения (всё что связано с requests)
db_session.global_init(db)  # Подключение БД
vk_session = vk_api.VkApi(token=bot_token)
session_api = vk_session.get_api()
longpoll = VkLongPoll(vk_session)


def get_user_data(user: int, fields: list, req_link: str) -> requests.get:
    """Получение данных пользователя в виде Словаря"""
    global app_token

    params = {
        'user_ids': user,
        'fields': fields,
        'access_token': app_token,
        'v': 5.131
    }
    request = requests.get(req_link, params=params).json()
    return request


def send_message(user: int, text: str) -> None:
    """Функция для отправления сообщения Ботом библиотекой vk_api"""
    message = {
        'user_id': user,
        'message': text,
        'random_id': 0
    }
    vk_session.method('messages.send', message)


def is_admin(user: int) -> bool:
    """Смотрит БД. Если пользователь администратор - возвращает True"""
    db_sess = db_session.create_session()
    user_data = db_sess.query(User).filter(User.id == str(user)).first()
    return user_data.is_admin


def add_user_to_database(user: int) -> None:
    """Добавление Пользователя в БД"""
    db_sess = db_session.create_session()

    if not db_sess.query(User).filter(User.id == str(user)).first():
        link = 'https://api.vk.com/method/users.get'
        req = get_user_data(user, 'bdate', link).get('response')[0]

        user_name = req.get('first_name')
        user_surname = req.get('last_name')
        user_bdate = req.get('bdate')

        user_data = User(id=user, name=user_name, surname=user_surname, birthday=user_bdate,
                         is_birthday=True, is_admin=False, is_banned=False)
        db_sess.add(user_data)
        db_sess.commit()


def call_group_admin(user: int) -> None:
    """Пишет всем администраторам Бота, что их зовёт пользователь"""
    req_link = 'https://api.vk.com/method/users.get'
    req = get_user_data(user, 'bdate', req_link).get('response')[0]

    user_name = req.get('first_name')
    user_surname = req.get('last_name')

    db_sess = db_session.create_session()
    admins = db_sess.query(User).filter(User.is_admin).all()
    if admins:
        text = f'Пользователь [id{user}|{user_name} {user_surname}] позвал администратора!'
        for admin in admins:
            send_message(admin.id, text)


def create_admin_code() -> str:
    """Создаёт код Администрации"""
    symbols = str(ascii_lowercase) + str(digits)
    db_sess = db_session.create_session()

    while True:
        admin_code = ''.join([choice(symbols) for _ in range(25)])

        if not db_sess.query(AdminCode).filter(AdminCode.code == admin_code).first():
            admin_code_data = AdminCode(code=admin_code, is_used=False)
            db_sess.add(admin_code_data)
            db_sess.commit()
            return admin_code


def use_admin_code(user: int, admin_code: str) -> bool:
    """Использование кода Администратора, назначение пользователя Администратором"""
    db_sess = db_session.create_session()
    user_data = db_sess.query(User).filter(User.id == str(user)).first()

    if not user_data.is_admin:
        admin_code_data = db_sess.query(AdminCode).filter(AdminCode.code == admin_code).first()

        if admin_code_data and not admin_code_data.is_used:
            user_data.is_admin = True
            admin_code_data.is_used = True
            db_sess.commit()
            return True

    return False


def tell_admin_info(text: str) -> None:
    """Рассылка всем администратором сообщения"""
    db_sess = db_session.create_session()
    admins = db_sess.query(User).filter(User.is_admin).all()

    if admins:
        for admin in admins:
            send_message(admin.id, text)


def add_redemption_code(code: str, end_date: str) -> bool:
    """Добавление Кода Погашения в БД"""
    db_sess = db_session.create_session()
    code_query = db_sess.query(RedemptionCode).filter(RedemptionCode.code == code).first()

    if not code_query:
        redemption_code = RedemptionCode(code=code, end_date=end_date)
        db_sess.add(redemption_code)
        db_sess.commit()
        return True

    return False


def main():
    """Главная функция Бота"""
    for event in longpoll.listen():
        if event.to_me:  # Каждый раз, если пользователь написал сообщение - Бот добавляет его в БД
            user_id = event.user_id
            add_user_to_database(user_id)

        if event.to_me and event.from_user and 'бот' in event.text.lower() and \
                event.text.lower().split()[0] == 'бот':  # Если Боту пишет пользователь в ЛС
            user_id, message = event.user_id, ' '.join(event.text.lower().split()[1:])

            if not message.strip():  # Если Пользователь отправил просто сообщение "бот"
                link = 'https://vk.com/@afk_arena-komandy-bota-v-ls-soobschestva'
                text = f'Привет! Я - бот сообщества [afk_arena|AFK Arena]. ' \
                       f'Мои команды ты можешь посмотреть по ссылке:\n{link}'
                send_message(user_id, text)

            elif message == 'админ':  # Пользователь зовёт Администратора. Надеюсь не пожалею о том, что добавил такую функцию
                text = 'Зову Администратора!'
                send_message(user_id, text)
                call_group_admin(user_id)

            elif message == 'коды':  # Список Кодов Возмещения, которые есть в Боте
                db_sess = db_session.create_session()
                redemption_codes = db_sess.query(RedemptionCode).all()
                text = '\n'.join([f'{k + 1}. Код: {i.code} | Действует до: {i.end_date}'
                                  for k, i in enumerate(redemption_codes)])
                send_message(user_id, text)

            elif message == 'др':  # Включает/Отключает поздравление с Днем Рождения
                db_sess = db_session.create_session()
                user_info = db_sess.query(User).filter(User.id == user_id).first()
                user_birthday = user_info.is_birthday
                user_info.is_birthday = not user_birthday
                db_sess.commit()

                if user_birthday:
                    text = 'Рассылка поздравлений отключена'
                else:
                    text = 'Рассылка поздравлений включена'
                send_message(user_id, text)

            elif 'код - ' in message:  # Использование кода Администратора
                try:
                    admin_code = message.split(' - ')[-1]

                    if use_admin_code(admin_code, admin_code):
                        text = 'Код успешно активирован. Вы получили роль Администратора Бота'
                        send_message(user_id, text)

                        link = 'https://api.vk.com/method/users.get'
                        admin_id_data = get_user_data(user_id, '', link).get('response')[0]

                        name = admin_id_data.get('first_name')
                        surname = admin_id_data.get('last_name')
                        text = f'Новый администратор Бота: [id{user_id}|{name} {surname}]'
                        tell_admin_info(text)

                    else:
                        text = 'Код администратора неправильный или уже был использован!'
                        send_message(user_id, text)

                except Exception:
                    text = 'Неправильное использование команды или Баг в работе Бота'
                    send_message(user_id, text)

        if event.to_me and event.from_user and 'админ' in event.text.lower() and \
                event.text.lower().split()[0] == 'админ' and is_admin(event.user_id):  # Если Боту пишет Администратор в ЛС
            admin_id, message = event.user_id, ' '.join(event.text.split()[1:])

            if message == 'код':  # Создание кода Администратора
                admin_code = create_admin_code()
                text = f'Новый код Администратора Бота:\n' \
                       f'{admin_code}\n\n' \
                       f'Код работает только 1 раз!'
                send_message(admin_id, text)

            elif 'код - ' in message:  # Добавление кода Возмещения в БД
                try:
                    redemption_code, end_date = message.split(' - ')[-2], message.split(' - ')[-1]

                    if add_redemption_code(redemption_code, end_date):
                        text = f'Код Возмещения "{redemption_code}" успешно добавлен'
                        send_message(admin_id, text)

                    else:
                        text = f'Такой Код уже есть!'
                        send_message(admin_id, text)

                except Exception as e:
                    text = f'Неправильное использование команды или Баг в работе Бота\n{e}'
                    send_message(admin_id, text)

            elif 'разжаловать' in message:  # Снимает роль Администратора
                try:
                    admin_id_2 = message.split(' - ')[-1]
                    if is_admin(admin_id_2):
                        db_sess = db_session.create_session()
                        admin = db_sess.query(User).filter(User.id == admin_id_2).first()
                        admin.is_admin = False
                        name_2 = admin.name
                        surname_2 = admin.surname
                        db_sess.commit()

                        link = 'https://api.vk.com/method/users.get'
                        user_id_data = get_user_data(admin_id, '', link).get('response')[0]
                        name = user_id_data.get('first_name')
                        surname = user_id_data.get('last_name')
                        text = f'[id{admin_id}|{name} {surname}] забрал роль Администратора у ' \
                               f'[id{admin_id_2}|{name_2} {surname_2}]'
                        tell_admin_info(text)

                    else:
                        text = 'Данный ID не принадлежит администратору Бота!'
                        send_message(admin_id, text)

                except Exception:
                    text = 'Неправильное использование команды или Баг в работе Бота'
                    send_message(admin_id, text)

            elif message == 'обновить бд':
                text = 'Обновляю список...'
                send_message(admin_id, text)

                db_sess = db_session.create_session()
                users_data = db_sess.query(User).all()

                logs = []
                for k, user in enumerate(users_data):
                    link = 'https://api.vk.com/method/users.get'
                    req = get_user_data(user.id, 'bdate', link).get('response')[0]
                    user_birthday = req.get('bdate')

                    if user.birthday != user_birthday:
                        old_birthday = user.birthday
                        user.birthday = user_birthday
                        logs_text = f'[id{user.id}|{user.name} {user.surname}] | ' \
                                    f'{old_birthday} -> {user_birthday}'
                        logs.append(logs_text)

                db_sess.commit()
                text = 'Завершено.\n\n' + '\n'.join(logs)
                send_message(admin_id, text)


if __name__ == '__main__':
    main()
