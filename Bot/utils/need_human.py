from random import random
from tokenize import endpats

from aiohttp.hdrs import EXPIRES
from vkbottle.bot import Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from config import admin_ids
from loader import bot

import logging
import datetime
import json

logging.basicConfig(filename= 'files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

class User:
    def __init__(self, user_id, first_name, last_name, status=True, text_message='Нужна помощь', start_time=None, end_time=None):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.status = status
        self.text_message = text_message
        self.start_time = start_time if start_time else datetime.datetime.now()
        self.end_time = end_time
        logger.info(f'add new user {self.user_id}')

    async def injson(self):
        data = {
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'status': self.status,
            'text_message': self.text_message,
            'start_time': self.start_time.strftime('%d.%m.%Y %H:%M'),
            'end_time': self.end_time
        }

        # Открываем файл и добавляем нового пользователя
        try:
            # Сначала пытаемся прочитать существующих пользователей
            with open('files/users.json', 'r') as f:
                try:
                    users = json.load(f)
                except json.JSONDecodeError:
                    # Если файл пуст или поврежден, создаем пустой список
                    users = []

            # Добавляем нового пользователя
            users.append(data)

            # Перезаписываем файл с новыми данными
            with open('files/users.json', 'w') as f:
                json.dump(users, f, indent=4, ensure_ascii=False)

            logger.info(f'add new user {self.user_id}')
        except Exception as e:
            logger.error(f"Error saving user {self.user_id}: {e}")

    async def send_message_admin(self):
        keyboard = (Keyboard(inline=True)
                    .add(Text("Завершить", payload={'command': 'finish_help', 'user_id': self.user_id}), color=KeyboardButtonColor.POSITIVE)
                    ).get_json()
        for admin_id in admin_ids:
            await bot.api.messages.send(
                peer_id=admin_id,
                message=f'Пользователь {self.first_name} {self.last_name} ({self.user_id}) обратился за помощью\n\n'+
                        f'Текст сообщения: {self.text_message}\n\n Время обращения: {self.start_time.strftime("%d.%m.%Y %H:%M")}',
                random_id=0,
                keyboard=keyboard
            )


def get_user(user_id: int) -> dict:
    try:
        with open('files/users.json', 'r') as f:
            users = json.load(f)

        # Ищем пользователя по ID в списке
        for user in users:
            if user['user_id'] == user_id:
                return user
        return None
    except Exception as e:
        logger.error(f"Error loading users.json: {e}")
        return None

async def update_status(user_id: int, new_status: bool) -> bool:
    try:
        user = get_user(user_id)
        if user is not None:
            # Обновляем статус и время
            user['status'] = new_status
            user['end_time'] = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')

            # Считываем текущие данные
            with open('files/users.json', 'r') as f:
                users = json.load(f)

            # Находим пользователя и обновляем его данные
            for idx, u in enumerate(users):
                if u['user_id'] == user_id:
                    users[idx] = user
                    break

            # Перезаписываем данные в файл
            with open('files/users.json', 'w') as f:
                json.dump(users, f, indent=4, ensure_ascii=False)

            logger.info(f'Updated user {user_id} status to {new_status}')
            return [True, user_id]
        else:
            logger.warning(f'User {user_id} not found')
            return [False, 'User not found']
    except Exception as e:
        logger.error(f'Error updating user {user_id}: {e}')
        return [False, str(e)]

async def delete_user(user_id: int) -> bool:
    try:
        with open('files/users.json', 'r') as f:
            users = json.load(f)

        # Находим пользователя и удаляем его из списка
        users = [u for u in users if u['user_id'] != user_id]

        # Перезаписываем файл
        with open('files/users.json', 'w') as f:
            json.dump(users, f, indent=4, ensure_ascii=False)

        logger.info(f'delete user {user_id}')
        return True
    except Exception as e:
        logger.error(f'delete user {user_id} error: {e}')
        return False


async def finish_help(user_id: int) -> bool:
    try:
        success = await update_status(user_id, False)
        if success[0]:
            # Получаем данные о пользователе
            user = get_user(user_id)
            if user is None:
                logger.error(f"User {user_id} not found while finishing help")
                return False

            # Вычисляем время работы
            start_time = datetime.datetime.strptime(user['start_time'], '%d.%m.%Y %H:%M')
            end_time = datetime.datetime.now()
            time_spent = end_time - start_time
            time_spent_trim = datetime.timedelta(seconds=time_spent.seconds)

            # Формируем сообщение для пользователя
            keyboard = (
                Keyboard(one_time=True, inline=False)
                .add(Text("Хочу в чат"), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text("Хочу купить игру"), color=KeyboardButtonColor.PRIMARY)
                .add(Text("Другое", payload={"command": 'other'}), color=KeyboardButtonColor.SECONDARY)
            ).get_json()

            await bot.api.messages.send(
                peer_id=user_id,
                message=f'Это снова я - бот Midgard. Надеюсь, что тебе смогли помочь!',
                random_id=0,
                keyboard=keyboard
            )

            # Отправка сообщения с подробной информацией админам
            for peer_id in admin_ids:
                await bot.api.messages.send(
                    peer_id=peer_id,
                    message=f'Работа с пользователем {user["first_name"]} {user["last_name"]} ({user["user_id"]}) завершена.\n'
                            f'Заняло времени: {time_spent_trim}',
                    random_id=0
                )
            return [True, time_spent_trim]
        else:
            # Если что-то пошло не так, отправляем админам информацию об ошибке
            for peer_id in admin_ids:
                await bot.api.messages.send(
                    peer_id=peer_id,
                    message=f'Что-то пошло не так. Работа с пользователем {user_id} не завершена! {success[1]}',
                    random_id=0
                )
            return [False, 0]
    except Exception as e:
        logger.error(f'Error finish user {user_id}: {e}')
        return [False, 0]

async def check_help_id(id: int) -> bool:
    try:
        with open('files/users.json', 'r') as f:
            users = json.load(f)

        # Проверяем, есть ли пользователь с таким ID
        for user in users:
            if user['user_id'] == id and user['end_time'] is None:
                logger.info(f'user {id} is in json')
                return True

        logger.info(f'user {id} not found in json')
        return False

    except Exception as e:
        logger.error(f'Error checking user {id}: {e}')
        return False
