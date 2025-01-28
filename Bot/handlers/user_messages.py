from utils.need_human import get_user
from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, OpenLink, BaseStateGroup
from config import admin_ids
from loader import bot
from utils.need_human import User, check_help_id

import logging
import json
import re

logging.basicConfig(filename= 'files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bl = BotLabeler()

class State(BaseStateGroup):
    _request_problem = 0,
    _send_problem = 1

@bl.private_message(text='начать')
async def start_handler(message: Message):
    keyboard = (
        Keyboard(one_time=True, inline=False)
        .add(Text("Хочу в чат"), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Хочу купить игру"), color=KeyboardButtonColor.PRIMARY)
        .add(Text("Другое", payload={"command": 'other'}), color=KeyboardButtonColor.SECONDARY)
    ).get_json()
    await message.answer("Привет! Я бот Midgard! Я постараюсь помочь тебе с твоим вопросом. Нажми на кнопку", keyboard=keyboard)
    logger.info(f"Answer 'start' to {message.peer_id}")

@bl.private_message(state=State._request_problem)
async def problem_handler(message: Message):
    await bot.api.messages.send(peer_id=message.peer_id, message='Спасибо за сообщение! Мы обязательно ответим тебе в ближайшее время', random_id=0)
    await bot.state_dispenser.set(message.peer_id, State._send_problem)
    user = await message.get_user()
    usr = User(user.id, user.first_name, user.last_name, status=True, text_message=message.text)
    await usr.injson()
    await usr.send_message_admin()
    del usr
    logger.info(f"Answer 'problem' to {message.peer_id}")

@bl.private_message(text='Хочу в чат')
async def chat_handler(message: Message):
    keyboard = (
    Keyboard(one_time=True, inline=False)
        .add(OpenLink('https://vk.me/join/s0c3RgqtN_IBklkgAkGoHL0bo_MYL2X2Q9E=', label='Присоединиться'), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text("Назад", payload={"command": 'start'}), color=KeyboardButtonColor.NEGATIVE)
    ).get_json()
    await message.answer('''Лови! Ссылку на чат. Пожалуйста ознакомься с правилами в закрепленном сообщении чата.
                        Запомни, что оплачивать игры без разрешения *midg_game (администратора) запрещено!''', keyboard=keyboard)
    logger.info(f"Answer '' to {message.peer_id}")

@bl.private_message(text='Хочу купить игру')
async def game_handler(message: Message):
    keyboard = (
    Keyboard(one_time=True, inline=False)
        .add(OpenLink('https://vk.com/@psmid-faq', label='Узнать подробнее', payload={"command": 'start'}), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(OpenLink('https://vk.com/app6326142_-217283918', label='Отзывы', payload={"command":'start'}), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text("Назад", payload={"command": 'start'}), color=KeyboardButtonColor.NEGATIVE)
    ).get_json()
    await message.answer('''Чтобы купить игру, обратись к *midg_game (Midgard Games). 
                        Подробнее о том, как купить игру можешь узнать по кнопке ниже, а также ознакомиться с отзывами''', keyboard=keyboard)
    logger.info(f"Answer 'need_human' to {message.peer_id}")

@bl.raw_event('message_new')
async def handler_payload(event):
    print(event)
    try:
        payload = event['object']['message']['payload']
        payload = json.loads(payload)
        command = payload['command']
        if command == 'other': # Клавитаура с help
            keyboard = (
                Keyboard(one_time=True, inline=False)
                .add(OpenLink('https://vk.com/@psmid-faq', label='FAQ'), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(OpenLink('https://vk.com/app6326142_-217283918', label='Отзывы', payload={"command":'start'}), color=KeyboardButtonColor.PRIMARY)
                .add(Text("Позвать человека", payload={"command": 'need_human'}), color=KeyboardButtonColor.SECONDARY)
                .row()
                .add(Text("Назад", payload={"command": 'start'}), color=KeyboardButtonColor.NEGATIVE)
            ).get_json()
            await bot.api.messages.send(peer_id=event['object']['message']['peer_id'],
                                        message = 'Попробуй поискать свой вопрос в FAQ, возможно, на него уже ответили :)\n\n Если ты не нашёл вопроса, то нажми "Позвать человека" и тебе обязательно помогут',
                                        random_id = 0, keyboard=keyboard)
            logger.info(f"Answer 'other' to {event['object']['message']['peer_id']}")
        elif command == 'start':  # Back to main menu
            keyboard = (
                Keyboard(one_time=True, inline=False)
                .add(Text("Хочу в чат"), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text("Хочу купить игру"), color=KeyboardButtonColor.PRIMARY)
                .add(Text("Другое", payload={"command": 'other'}), color=KeyboardButtonColor.SECONDARY)
            ).get_json()
            await bot.api.messages.send(peer_id=event['object']['message']['peer_id'],
                                        message='Привет! Я бот Midgard! Я постараюсь помочь тебе с твоим вопросом. Нажми на кнопку',
                                        random_id=0, keyboard=keyboard)
            logger.info(f"Answer 'back to main menu' to {event['object']['message']['peer_id']}")

        elif command == 'need_human':  # Need human
            await bot.api.messages.send(peer_id=event['object']['message']['peer_id'],
            message = 'Напиши свой вопрос и я передам его поддержке', random_id=0)
            await bot.state_dispenser.set(event['object']['message']['peer_id'], State._request_problem)

    except Exception as e:
        logger.warning(f'Unknown payload: {e}')
        return

@bl.private_message(blocking=False)
async def ununderstand_handler(message: Message):
    try:
        list = ['Хочу в чат','Другое','FAQ','Отзывы','Хочу купить игру','Назад','Позвать человека','начать', 'Начать']
        if message.text in list:
            return
        if str(message.peer_id) in admin_ids:
            return
        if await check_help_id(message.peer_id) == True:
            return

        keyboard = (
            Keyboard(one_time=True, inline=False)
            .add(Text("Хочу в чат"), color=KeyboardButtonColor.PRIMARY)
            .row()
            .add(Text("Хочу купить игру"), color=KeyboardButtonColor.PRIMARY)
            .add(Text("Другое", payload={"command": 'other'}), color=KeyboardButtonColor.SECONDARY)
        ).get_json()

        await message.answer(f"Я не понял твой запрос: {message.text}. Но постараюсь помочь тебе. Нажми на кнопку", keyboard=keyboard)
        logger.info(f"Answer 'ununderstood' to {message.peer_id}")
    except Exception as e:
        logger.error(f"Error in tuta: {e}")