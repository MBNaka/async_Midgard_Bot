from tracemalloc import Statistic
from datetime import datetime

from vkbottle.bot import BotLabeler, Message
from vkbottle.dispatch.rules import ABCRule
from PIL import Image, ImageDraw, ImageFont
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup, PhotoMessageUploader, DocMessagesUploader
from utils.automatic_create_poll import auto_create_poll_commands, AutoCreatePoll
from utils.manual_create_poll import manual_create_poll_commands
from utils.manual_create_poll import get_poll, send_to_chat, delete_poll
from config import admin_ids, poll_commands, OWNER_ID_1, POLL_PEER_ID
from loader import bot
from utils.calc import startup_calc
from utils.fix_create_poll import _send_keyboard
from utils.check_polls import check_polls
from utils.need_human import finish_help
from utils.bot_statistics import send_report, add_request

import logging
import random
import string
import json

logging.basicConfig(filename='files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FromAdminRule(ABCRule[Message]):
    async def check(self, message: Message) -> bool:
        return str(message.from_id) in admin_ids

class StatisticState(BaseStateGroup):
    _get_period = 0,
    _get_date = 1
    _send_report = 2,
    _back = 3,

class CouponState(BaseStateGroup):
    _get_coupon = 0,
    _send_coupon = 1,
    _back = 2

async def generate_random_code(length):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

async def send_message(peer_id, message, payload=None, attachments=None, keyboard=None):
    await bot.api.messages.send(
        peer_id=peer_id,
        message=message,
        random_id=0,
        attachment=attachments,
        keyboard=keyboard,
        payload=payload
    )

async def event_send_keybrd(peer_id):
    keyboard = (
        Keyboard(one_time=True, inline=False)
        .add(Text('Создать опрос (автоматически)', payload={"command": "create_poll"}),
             color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text('Создать опрос (вручную)', payload={"command": "manual_create_poll"}),
             color=KeyboardButtonColor.PRIMARY)
        .add(Text('Калькулятор', payload={"command": "calc"}), color=KeyboardButtonColor.PRIMARY)
    ).get_json()

    await bot.api.messages.send(
        peer_id=peer_id,
        message='Нажми кнопку',
        random_id=0,
        keyboard=keyboard
    )
    logging.info(f'send keyboard in {peer_id}')

async def send_keyboard(message: Message):
    keyboard = (
        Keyboard(one_time=True, inline=False)
        .add(Text('Создать опрос (автоматически)', payload={"command": "create_poll"}), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text('Создать опрос (вручную)', payload={"command": "manual_create_poll"}),
             color=KeyboardButtonColor.PRIMARY)
        .add(Text('Калькулятор', payload={"command": "calc"}), color=KeyboardButtonColor.PRIMARY)
    ).get_json()

    await bot.api.messages.send(
        peer_id=message.peer_id,
        message='Нажми кнопку',
        random_id=0,
        keyboard=keyboard
    )
    logging.info(f'send_keyboard in {message.peer_id}')

bl = BotLabeler()
bl.auto_rules = [FromAdminRule()]

poll_instance = None
manual_poll_instance = None

@bl.private_message(text='Админпанель')
async def admin_panel(message: Message):
    keyboard = (Keyboard(one_time=True, inline=False)
                .add(Text('старт'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('Получить купон'), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text('Получить логи'), color=KeyboardButtonColor.NEGATIVE)
                .add(Text('Посмотреть статистику'), color=KeyboardButtonColor.SECONDARY)
                .row()
                .add(Text('Запустить проверку опросов'), color=KeyboardButtonColor.NEGATIVE)
                .add(Text('Эхо'), color=KeyboardButtonColor.PRIMARY)
                ).get_json()
    await message.answer('Добро пожаловать в панель администратора!\n\nстарт - создать опрос (автоматически или вручную) и калькулятор\nПолучить купон - генерация купона с кодом\nПолучить логи - в разработке\nПосмотреть статистику - работает криво\nЗапустить проверку опросов - в разработке\nЭхо - управление рассылкой', keyboard=keyboard)
    logger.info(f'admin_panel in {message.peer_id}')

@bl.private_message(text='Получить логи')
async def get_logs(message: Message):
    pass

@bl.private_message(text='Получить купон')
async def get_coupon(message: Message):
    await message.answer('Укажи номинал купона')
    await bot.state_dispenser.set(message.peer_id, CouponState._get_coupon)

@bl.private_message(state=CouponState._get_coupon)
async def send_coupon(message: Message):
    try:
        price_text = str(message.text)

        image = Image.open('files/template.png')
        draw = ImageDraw.Draw(image)
        size = 150 if int(price_text) < 10000 else 135
        price_font = ImageFont.truetype('fonts/montserrat-bold.ttf', size)
        code_font = ImageFont.truetype('fonts/montserrat-bold.ttf', 80)
        code = 'MID' + await generate_random_code(6)

        if int(price_text) >= 1000:
            x_coord = 80
        elif int(price_text) < 1000:
            x_coord = 150

        y_coord = 800
        if int(price_text) >= 10000:
            y_coord = 810


        draw.text((x_coord, y_coord), price_text, fill=(84, 189, 216), font=price_font)
        draw.text((820, 1000), code, fill=(255, 255, 255), font=code_font)

        image.save('files/coupon.png')

        photo_uploader = PhotoMessageUploader(bot.api)

        photo = await photo_uploader.upload(
            file_source='files/coupon.png',
            peer_id=message.peer_id,
        )
        message_text = f'Купон на сумму {price_text} рублей успешно сгенерирован. Код: {code}'
        await message.answer(message=message_text,attachment=photo)
        await send_keyboard(message)
    except Exception as e:
        await message.answer(f'Произошла ошибка: {e}')
    await bot.state_dispenser.set(message.peer_id, CouponState._back)

@bl.private_message(text='Посмотреть статистику')
async def get_stats(message: Message):
    keyboard = (Keyboard(one_time=True, inline=False)
        .add(Text('За текущий день'), color=KeyboardButtonColor.SECONDARY)
        .add(Text('За текущий месяц'), color=KeyboardButtonColor.SECONDARY)
        .add(Text('За текущий год'), color=KeyboardButtonColor.SECONDARY)
        .row()
        .add(Text('Указать свой период'), color=KeyboardButtonColor.SECONDARY)
        .add(Text('Админпанель'), color=KeyboardButtonColor.NEGATIVE)
    ).get_json()
    await message.answer('Выбери за какой период посмотреть статистику или вернись в админ панель', keyboard=keyboard)
    await bot.state_dispenser.set(message.peer_id, StatisticState._get_period)


@bl.private_message(state=StatisticState._get_period)
async def get_period(message: Message):
    today = datetime.now().date()  # Берем только дату (без времени)

    keyboard = (Keyboard(one_time=True, inline=False)
                .add(Text('Админпанель'), color=KeyboardButtonColor.NEGATIVE)
                ).get_json()

    def format_date(date):
        """Функция для преобразования даты в формат ДД.ММ.ГГГГ"""
        return date.strftime("%d.%m.%Y")

    if message.text == 'За текущий день':
        start_date = format_date(today)
        end_date = format_date(today)
        report = await send_report(message.peer_id, start_date, end_date)
        await message.answer(report, keyboard=keyboard)

    elif message.text == 'За текущий месяц':
        start_date = format_date(today.replace(day=1))
        end_date = format_date(today)
        report = await send_report(message.peer_id, start_date, end_date)
        await message.answer(report, keyboard=keyboard)

    elif message.text == 'За текущий год':
        start_date = format_date(today.replace(month=1, day=1))
        end_date = format_date(today)
        report = await send_report(message.peer_id, start_date, end_date)
        await message.answer(report, keyboard=keyboard)

    elif message.text == 'Указать свой период':
        await message.answer("Пока не работает")

@bl.private_message(text='старт')
async def start_poll(message: Message):
    await send_keyboard(message)
    logger.info(f'start_poll in {message.peer_id}')

@bl.private_message(text='Запустить проверку опросов')
async def manual_check_poll(message: Message):
    await message.answer('Запускаю проверку опросов')
    await check_polls()
    await message.answer('Проверка опросов завершена')

@bl.private_message(text='/help')
async def help(message: Message):
    await message.answer('старт - запустить клавиатуру\n /check_poll - проверка опросов\n /help - помощь')

@bl.raw_event('message_new', blocking=False)
async def handler_poll_payload(event):
    message = event['object']['message']['text']
    global poll_instance
    if message.startswith('https://store.playstation.com'):
        if poll_instance is None:
            poll_instance = AutoCreatePoll()
        await poll_instance.determine_way(event, link=True)
    try:
        payload = event['object']['message']['payload']
        payload = json.loads(payload)
        command = payload.get('command')
    except Exception as e:
        logging.warning(f'Error parsing payload: {e}')
        command = None

    if command == 'calc':
        success = await startup_calc(event['object']['message']['from_id'])
        if not success:
            await send_message(OWNER_ID_1, 'Не получилось запустить калькулятор. Проверь логи')
            await send_message(event['object']['message']['from_id'], 'Не удалось запустить калькулятор. Уведомил *mbnaka')
        return

    elif command in poll_commands:
        if poll_instance is None:
            poll_instance = AutoCreatePoll()
        await poll_instance.determine_way(event)
    elif command in auto_create_poll_commands:
        if command == 'auto_send_poll':
            await poll_instance.send_poll()
            await event_send_keybrd(event['object']['message']['from_id'])

        elif command == 'auto_fix_poll':
            poll = await poll_instance.get_poll()
            await _send_keyboard(poll, True, event['object']['message']['from_id'])

    elif command in manual_create_poll_commands:
        if command =='manual_send_poll':
            await send_to_chat(POLL_PEER_ID)
            logger.info(f'Send poll in main chat')
            await event_send_keybrd(event['object']['message']['from_id'])
            await delete_poll(event['object']['message']['from_id'])
            if not success:
                await send_message(OWNER_ID_1, 'Не получилось удалить экземпляр класса. Проверь логи')
            await send_message(event['object']['message']['from_id'], 'Опрос добавлен в чат')
            await event_send_keybrd(event['object']['message']['from_id'])

        elif command =='manual_cancel_poll':
            success = await manual_create_poll.delete_poll(event['object']['message']['from_id'])
            if not success:
                await send_message(OWNER_ID_1, 'Не получилось удалить экземпляр класса. Проверь логи')
                await send_message(event['object']['message']['from_id'],
                                        'Не удалось удалить опрос. Уведомил *mbnaka')
            else:
                await send_message(event['object']['message']['from_id'], 'Отменил создание опроса')
            await event_send_keybrd(event['object']['message']['from_id'])

        elif command =='manual_fix_poll':
            poll = await get_poll()
            await _send_keyboard(poll, False, event['object']['message']['from_id'])

    if command == 'finish_help':
        user_id = payload.get('user_id')
        success = await finish_help(int(user_id))
        minutes_spent = success[1].total_seconds() / 60
        await add_request(minutes_spent)
        if success[0]:
            logger.info('Finish help is successful')
        else:
            logger.info('Finish help is not successful')


    else:
        logger.info(f'Unknown command: {command}')
