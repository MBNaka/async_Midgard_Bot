from vkbottle.bot import Message, BotLabeler
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup
from vkbottle.dispatch.rules import ABCRule
from utils.google_sheets import GoogleSheets, save_poll
from config import OWNER_ID_2, POLL_PEER_ID, admin_ids
from loader import midg_user_bot, bot, adm_user_bot

import re
import json
import logging

logging.basicConfig(filename='files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

manual_create_poll_commands = ['manual_send_poll', 'manual_fix_poll', 'manual_cancel_poll']

poll = None

class FromAdminRule(ABCRule[Message]):
    async def check(self, message: Message) -> bool:
        return str(message.from_id) in admin_ids

bl = BotLabeler()
bl.auto_rules = [FromAdminRule()]

class States(BaseStateGroup):
    _title = 0
    _description = 1
    _picture = 2
    _ps_type = 3
    _country = 4
    _filling_method = 5
    _price = 6
    _determine_prices = 7
    _create_poll = 8
    _pre_send = 9
    _send = 10

class Poll:
    def __init__(self, title, description=None, picture=None,
                 ps_type=None, country=None, dlc=None, price=None,
                 keyboard=None, message=None, attachments=None, filling_method=None, step=None,
                 T2P2_price=None, T3P3_price=None, P2_price=None, P3_price=None
                 ):
        self.title = title
        self.description = description
        self.picture = picture
        self.poll = poll
        self.ps_type = ps_type
        self.country = country
        self.dlc = dlc
        self.price = price
        self.keyboard = keyboard
        self.message = message
        self.attachments = attachments
        self.filling_method = filling_method
        self.step = step
        self.T2P2_price = T2P2_price
        self.T3P3_price = T3P3_price
        self.P2_price = P2_price
        self.P3_price = P3_price

@bl.private_message(lev='Создать опрос (вручную)')
async def title(message: Message):
    await message.answer("Напиши название игры:")
    await bot.state_dispenser.set(message.peer_id, States._description)
    logger.info(f'Запущен процесс ручного создания опроса от {message.peer_id}')

@bl.private_message(lev='отмена')
async def cancel(message: Message):
    keyboard = (
        Keyboard(one_time=True, inline=False)
        .add(Text('Создать опрос (автоматически)', payload={"command": "create_poll"}),
             color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text('Создать опрос (вручную)', payload={"command": "manual_create_poll"}),
             color=KeyboardButtonColor.PRIMARY)
        .add(Text('Калькулятор', payload={"command": "calc"}), color=KeyboardButtonColor.PRIMARY)
    ).get_json()
    await message.answer("Понял. Отменяю", keyboard=keyboard)
    await bot.state_dispenser.delete(message.peer_id)
    logger.info(f'User {message.peer_id} canceled create poll')

@bl.private_message(state=States._description)
async def description(message: Message):
    global poll
    poll = Poll(title=message.text)
    logger.info(f'Получено название: {message.text}')
    keyboard = (Keyboard(one_time=True, inline=False)
                .add(Text('Русская озвучка'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('Русские субтитры'), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text('Русский язык'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('Английский язык'), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text('Не содержит основную игру'), color=KeyboardButtonColor.PRIMARY)
                ).get_json()
    await message.answer("Напиши описание: ", keyboard=keyboard)
    logger.info('Запрос описания')
    await bot.state_dispenser.set(message.peer_id, States._picture)

@bl.private_message(state=States._picture)
async def picture(message: Message):
    global poll
    poll.description = message.text
    logger.info(f'Получено описание: {message.text}')
    await message.answer("Отправь картинку")
    logger.info('Запрос картинки')
    await bot.state_dispenser.set(message.peer_id, States._ps_type)

@bl.private_message(state=States._ps_type)
async def ps_type(message: Message):
    global poll
    picture = message.get_photo_attachments()
    photo = picture[0]
    access_key = photo.access_key
    id = photo.id
    owner_id = photo.owner_id
    picture = f'photo{owner_id}_{id}_{access_key}'
    if picture is None:
        await message.answer("Произошла какая-то ошибка. Отправь картинку снова")
        logger.info('Ошибка получения картинки')
        return
    else:
        logger.info(f'Получена картинка: {picture}')
        poll.picture = picture
        keyboard = (Keyboard(one_time=True, inline=False)
                    .add(Text('PS4, PS5'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('PS5'), color=KeyboardButtonColor.PRIMARY)
                    .row()
                    .add(Text('DLC'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('PS PLUS'), color=KeyboardButtonColor.PRIMARY)
                    ).get_json()
        await message.answer("Выбери тип опроса: ", keyboard=keyboard)
        logger.info('Запрос типа опроса')
        await bot.state_dispenser.set(message.peer_id, States._country)

@bl.private_message(state=States._country)
async def country(message: Message):
    global poll
    if poll.ps_type is None:
        logger.info(f'Определение типа опроса')
        poll.ps_type = await determine_ps_type(message)
        if poll.ps_type is None:
            logger.error(f'Произошла ошибка при определении типа опроса. Повторяю попытку')
            keyboard = (Keyboard(one_time=True, inline=False)
                        .add(Text('PS4, PS5'), color=KeyboardButtonColor.PRIMARY)
                        .add(Text('PS5'), color=KeyboardButtonColor.PRIMARY)
                        .row()
                        .add(Text('DLC'), color=KeyboardButtonColor.PRIMARY)
                        .add(Text('PS PLUS'), color=KeyboardButtonColor.PRIMARY)
                        ).get_json()
            await message.answer("Произошла какая-то ошибка. Выбери тип снова", keyboard=keyboard)
            return
        logger.info(f'Тип опроса: {poll.ps_type}')
        poll.step = None
    if poll.ps_type == 'need_request_DLC' and poll.step == None:
        keyboard = (Keyboard(one_time=True, inline=False)
                    .add(Text('DLC PS5'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('DLC PS4'), color=KeyboardButtonColor.PRIMARY)
                    ).get_json()
        await message.answer("Выбери тип опроса для DLC: ", keyboard=keyboard)
        logger.info('Запрос типа DLC')
        poll.step = 'DLC'
    elif poll.ps_type == 'need_request_PS_PLUS' and poll.step == None:
        keyboard = (Keyboard(one_time=True, inline=False)
                    .add(Text('PS PLUS PS5'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('PS PLUS PS4'), color=KeyboardButtonColor.PRIMARY)
                    ).get_json()
        await message.answer("Выбери тип опроса для PS PLUS: ", keyboard=keyboard)
        logger.info('Запрос типа PS PLUS')
        poll.step = 'PS_PLUS'
    elif poll.ps_type == 'need_request_DLC' and poll.step == 'DLC':
        logger.info('Определение типа DLC')
        poll.ps_type = await determine_ps_type(message, repeat=True, select=poll.step)
        logger.info(f'Тип DLC: {poll.ps_type}')
        poll.step = None
        await request_country(message)
        await bot.state_dispenser.set(message.peer_id, States._filling_method)
    elif poll.ps_type == 'need_request_PS_PLUS' and poll.step == 'PS_PLUS':
        logger.info('Определение типа PS PLUS')
        poll.ps_type = await determine_ps_type(message, repeat=True, select=poll.step)
        logger.info(f'Тип PS PLUS: {poll.ps_type}')
        poll.step = None
        poll.filling_method = 'Вручную'
        poll.step = await request_prices(message)
        await bot.state_dispenser.set(message.peer_id, States._determine_prices)
    else:
        await request_country(message)
        await bot.state_dispenser.set(message.peer_id, States._filling_method)

@bl.private_message(state=States._filling_method)
async def filling_method(message: Message):
    global poll
    poll.country = message.text
    logger.info(f'Получено страна: {message.text}')
    keyboard = (Keyboard(one_time=True, inline=False)
                .add(Text('Автоматически'), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text('Вручную'), color=KeyboardButtonColor.SECONDARY)
                ).get_json()
    await message.answer("Выбери способ заполнения: ", keyboard=keyboard)
    logger.info('Запрос способа заполнения')
    await bot.state_dispenser.set(message.peer_id, States._price)

@bl.private_message(state=States._price)
async def price(message: Message):
    global poll
    poll.filling_method = message.text
    logger.info(f'Способ заполнения: {poll.filling_method}')
    if poll.filling_method == 'Автоматически':
        await message.answer("Напиши цену: ")
        await bot.state_dispenser.set(message.peer_id, States._determine_prices)
    elif poll.filling_method == 'Вручную':
        poll.step = await request_prices(message)
        await bot.state_dispenser.set(message.peer_id, States._determine_prices)

@bl.private_message(state=States._determine_prices)
async def determine_prices(message: Message):
    global poll
    if poll.filling_method == 'Автоматически':
        poll.price = message.text
        await set_typing_status(message.peer_id)
        google_sheet = GoogleSheets(poll.ps_type, poll.price, poll.country)
        if re.search(r'DLC', poll.ps_type):
            poll.price = await google_sheet.dlc_price()
            await create_poll(message)
            await send_message(message)
            await bot.state_dispenser.set(message.peer_id, States._create_poll)
        elif poll.ps_type == 'PS5' or poll.ps_type == 'PS4, PS5':
            poll.price = await google_sheet.determine_price()
            await extract_prices(poll.price)
            await create_poll(message)
            await send_message(message)
            await bot.state_dispenser.set(message.peer_id, States._create_poll)
    elif poll.filling_method == 'Вручную':
        if poll.step is None:
            poll.step = await request_prices(message, poll.step)
        elif poll.step is not None:
            poll.step = await request_prices(message, poll.step)
        if poll.step == 'Done':
            await create_poll(message)
            poll.step = '123'
            await send_message(message)

async def determine_ps_type(message: Message, repeat: bool = False, select: str = None):
    try:
        if repeat is False:
            if message.text == 'PS4, PS5' or message.text == 'PS5':
                return message.text
            elif message.text == 'DLC':
                return 'need_request_DLC'
            elif message.text == 'PS PLUS':
                return 'need_request_PS_PLUS'
        elif repeat is True and select == 'DLC':
            if message.text == 'DLC PS5':
                return 'DLC_PS5'
            elif message.text == 'DLC PS4':
                return 'DLC_PS4'
        elif repeat is True and select == 'PS_PLUS':
            if message.text == 'PS PLUS PS5':
                return 'PS_PLUS_PS5'
            elif message.text == 'PS PLUS PS4':
                return 'PS_PLUS_PS4'
    except Exception as e:
        logger.error(f'Error determine ps type: {e}')
        return None

async def request_country(message: Message):
    keyboard = (Keyboard(one_time=True, inline=False)
                .add(Text('Турция'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('Украина'), color=KeyboardButtonColor.PRIMARY)
                ).get_json()
    await message.answer("Выбери страну: ", keyboard=keyboard)
    logger.info('Запрос страны')
    return

async def request_prices(message: Message, step: any = None):
    global poll
    if step == None:
        if poll.ps_type == 'PS5':
            await message.answer("Напиши цену П2: ")
            logger.info(f'step: {step}. Request P2 price')
            step = 1
        if poll.ps_type == 'PS4, PS5':
            await message.answer("Напиши цену Т2/П2: ")
            logger.info(f'step: {step}. Request T2/P2 price')
            step = 1
        if poll.ps_type == 'DLC_PS5' or poll.ps_type == 'DLC_PS4':
            await message.answer('Напиши цену одной позиции: ')
            logger.info(f'step: {step}. Request DLC price')
            step = 'finish'
        if poll.ps_type == 'PS_PLUS_PS5' or poll.ps_type == 'PS_PLUS_PS4':
            await message.answer('Напиши цену П2: ')
            logger.info(f'step: {step}. Request P2 price for PS PLUS')
            step = 1
    elif step == 1:
        if poll.ps_type == 'PS5':
            poll.P2_price = message.text
            logger.info(f'step: {step}. Get P2 price: {poll.P2_price}')
            await message.answer("Напиши цену П3: ")
            logger.info(f'step: {step}. Request P3 price')
            step = 'finish'
        if poll.ps_type == 'PS4, PS5':
            poll.T2P2_price = message.text
            logger.info(f'step: {step}. Get T2/P2 price: {poll.T2P2_price}')
            await message.answer("Напиши цену Т3/П3: ")
            logger.info(f'step: {step}. Request T3/P3 price')
            step = 'finish'
        if poll.ps_type == 'PS_PLUS_PS5':
            poll.P2_price = message.text
            logger.info(f'step: {step}. Get P2 price for PS PLUS: {poll.P2_price}')
            await message.answer('Напиши цену П3: ')
            logger.info(f'step: {step}. Request P3 price for PS PLUS')
            step = 'finish'
        if poll.ps_type == 'PS_PLUS_PS4':
            poll.P2_price = message.text
            logger.info(f'step: {step}. Get P2 price for PS PLUS: {poll.T2P2_price}')
            await message.answer('Напиши цену Т3/П3: ')
            logger.info(f'step: {step}. Request T3/P3 price for PS PLUS')
            step = 'finish'
    elif step == 'finish':
        if poll.ps_type == 'PS5':
            poll.P3_price = message.text
            logger.info(f'step: {step}. Get P3 price: {poll.P3_price}')
            step = 'Done'
        if poll.ps_type == 'PS4, PS5':
            poll.T3P3_price = message.text
            logger.info(f'step: {step}. Get T3/P3 price: {poll.T3P3_price}')
            step = 'Done'
        if poll.ps_type == 'DLC_PS5' or 'DLC_PS4':
            poll.price = message.text
            logger.info(f'step: {step}. Get DLC price: {poll.price}')
            step = 'Done'
        if poll.ps_type == 'PS_PLUS_PS5':
            poll.P3_price = message.text
            logger.info(f'step: {step}. Get P3 price for PS PLUS: {poll.P3_price}')
            step = 'Done'
        if poll.ps_type == 'PS_PLUS_PS4':
            poll.T3P3_price = message.text
            logger.info(f'step: {step}. Get T3/P3 price for PS PLUS: {poll.T3P3_price}')
            step = 'Done'

    logger.info(f'step: {step}')
    return step

async def extract_prices(prices_dict: dict) -> bool:
    try:
        global poll
        if 'price_T2P2' in prices_dict:
            poll.T2P2_price = prices_dict['price_T2P2']
            logger.info(f'Get T2P2_price - {poll.T2P2_price}')
        if 'price_T3P3' in prices_dict:
            poll.T3P3_price = prices_dict['price_T3P3']
            logger.info(f'Get T3P3_price - {poll.T3P3_price}')
        if 'price_P2' in prices_dict:
            poll.P2_price = prices_dict['price_P2']
            logger.info(f'Get P2_price - {poll.P2_price}')
        if 'price_P3' in prices_dict:
            poll.P3_price = prices_dict['price_P3']
            logger.info(f'Get P3_price - {poll.P3_price}')
        return True
    except Exception as e:
        logger.error(f'Error extract prices: {e}')
        return False

async def create_poll(message: Message):
    global poll
    logger.info(f'Starting Create poll')
    question = 'Бронь'
    answers = []

    if poll.ps_type == 'PS5':
        answers.append(f'П2 - {poll.P2_price}р')
        answers.append(f'П3 - {poll.P3_price}р')
    elif poll.ps_type == 'PS4, PS5':
        answers.append(f'Т2/П2 - {poll.T2P2_price}р')
        answers.append(f'Т3 - {poll.T3P3_price}р')
        answers.append(f'П3 - {poll.T3P3_price}р')
    elif poll.ps_type == 'DLC_PS5':
        answers.append(f'П3 - {poll.price}р')
    elif poll.ps_type == 'DLC_PS4':
        answers.append(f'Т3 - {poll.price}р')
        answers.append(f'П3 - {poll.price}р')
    elif poll.ps_type == 'PS_PLUS_PS5':
        answers.append(f'П2 - {poll.P2_price}р')
        answers.append(f'П3 - {poll.P3_price}р')
    elif poll.ps_type == 'PS_PLUS_PS4':
        answers.append(f'П2 - {poll.P2_price}р')
        answers.append(f'Т3 - {poll.T3P3_price}р')
        answers.append(f'П3 - {poll.T3P3_price}р')
    answers.append('Просто кнопка')
    logger.info(f'Answers saved: {answers}')

    result = await midg_user_bot.polls.create(
        question=question,
        add_answers=json.dumps(answers),
        owner_id=OWNER_ID_2
    )
    poll_id = result.id
    poll.poll = f'poll{OWNER_ID_2}_{poll_id}'
    logger.info(f'Success create poll - {poll.poll}')
    return

async def send_message(message: Message):
    global poll
    text = (f'{poll.title}&#128293;\n\n'
               f'{poll.description}\n\n'
               'Желающие собрать бронируем места в опросе &#128071;\n\n'
               'Если вы не готовы купить позицию, не голосуйте!'
               )
    attachments = f"{poll.picture},{poll.poll}"
    keyboard = (
        Keyboard(one_time=True, inline=False)
        .add(Text('Отправить', payload={"command": "manual_send_poll"}), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text('Исправить', payload={"command": "manual_fix_poll"}), color=KeyboardButtonColor.NEGATIVE)
        .row()
        .add(Text('Отмена', payload={"command": "manual_cancel_poll"}), color=KeyboardButtonColor.SECONDARY)
    ).get_json()
    await message.answer(message=text, keyboard=keyboard, attachment=attachments)

    logger.info(f'Success pre_send poll to {message.peer_id}. title:{poll.title}')
    return

async def send_to_chat(peer_id: int = POLL_PEER_ID) -> None:
    global poll
    text = (f'{poll.title}&#128293;\n\n'
            f'{poll.description}\n\n'
            'Желающие собрать бронируем места в опросе &#128071;\n\n'
            'Если вы не готовы купить позицию, не голосуйте!')
    attachments = f"{poll.picture},{poll.poll}"
    await bot.api.messages.send(
        peer_id=peer_id,
        random_id=0,
        message=text,
        attachment=attachments
    )
    success = await save_poll(poll)
    await add_vote(poll)
    if success:
        logger.info(f'Success send and save poll to {peer_id}. title:{poll.title}')
    else:
        logger.error(f'Error save and send poll to {peer_id}. title:{poll.title}.')
    return

async def add_vote(poll: Poll) -> bool:
    try:
        poll_id = int(poll.poll.split('_')[1])
        result = await midg_user_bot.polls.get_by_id(poll_id)
        answer_ids = result.answers
        for answer in answer_ids:
            if answer.text == 'Просто кнопка':
                answer_id = answer.id
        await midg_user_bot.polls.add_vote(answer_id, poll_id)
        await adm_user_bot.polls.add_vote(answer_id, poll_id)
        logger.info(f'Success add vote')
        return True
    except Exception as e:
        logger.error(f'Error get add_vote - {e}')
        return False


async def set_typing_status(peer_id: str, type: str='typing') -> bool:
    try:
        await bot.api.messages.set_activity(
            type=type,
            peer_id=str(peer_id)
        )
        return True
    except Exception as e:
        logger.error(f'Error set typing status - {e}')
        return False

async def get_poll():
    global poll
    logger.info('Return manual create poll')
    return poll

async def delete_poll(peer_id: str) -> bool:
    try:
        await bot.state_dispenser.delete(peer_id)
        logger.info('Delete poll')
        return True
    except Exception as e:
        logger.error(f'Error manual delete poll - {e}')
        return False