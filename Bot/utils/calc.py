from vkbottle.bot import Message, BotLabeler
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup
from utils.google_sheets import GoogleSheets
from vkbottle.dispatch.rules import ABCRule
from config import admin_ids
from loader import bot

import re
import json
import logging

logging.basicConfig(filename='files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FromAdminRule(ABCRule[Message]):
    async def check(self, message: Message) -> bool:
        return str(message.from_id) in admin_ids

cbl = BotLabeler()
cbl.auto_rules = [FromAdminRule()]

calc = None

class calc_states(BaseStateGroup):
    waiting_country = 0
    waiting_type = 1
    waiting_price = 2
    waiting_answer = 3

class cl_calc:
    def __init__(self):
        self.country = None
        self.type = None
        self.price = None
        self.P2_price = None
        self.P3_price = None
        self.T2P2_price = None
        self.T3P3_price = None

"""MAIN FUNCTION"""

async def startup_calc(peer_id: int) -> bool:
    try:
        global calc
        calc = cl_calc()
        text = "Выбери страну:"
        keyboard = (Keyboard(one_time=True)
                    .add(Text('Турция'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('Украина'), color=KeyboardButtonColor.PRIMARY)
                    ).get_json()
        await bot.api.messages.send(peer_id=peer_id, message=text, keyboard=keyboard, random_id=0)
        await bot.state_dispenser.set(peer_id, calc_states.waiting_country)
        logger.info(f'startup_calc({peer_id})')
        return True
    except Exception as e:
        logger.error(f'Error in startup_calc: {e}')
        return False

"""UTILS"""

@cbl.private_message(state=calc_states.waiting_country)
async def waiting_country(message: Message):
    global calc
    calc.country = 'Turkey' if message.text == 'Турция' else 'Ukraine'

    text = "Выбери тип:"
    keyboard = (Keyboard(one_time=True)
                .add(Text('PS4, PS5'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('PS5'), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text('DLC PS4'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('DLC PS5'), color=KeyboardButtonColor.PRIMARY)
                ).get_json()

    await message.answer(message=text, keyboard=keyboard, random_id=0)
    await bot.state_dispenser.set(message.peer_id, calc_states.waiting_type)

    logger.info(f'waiting_type({message.peer_id})')

@cbl.private_message(state=calc_states.waiting_type)
async def waiting_type(message: Message):
    if message.text == 'PS4, PS5':
        calc.type = 'PS4, PS5'
    elif message.text == 'PS5':
        calc.type = 'PS5'
    elif message.text == 'DLC PS4':
        calc.type = 'DLC_PS4'
    else:
        calc.type = 'DLC_PS5'

    text = 'Введи цену'
    await message.answer(message=text, random_id=0)
    await bot.state_dispenser.set(message.peer_id, calc_states.waiting_price)
    logger.info(f'waiting_price({message.peer_id})')

@cbl.private_message(state=calc_states.waiting_price)
async def waiting_price(message: Message):
    global calc
    calc.price = message.text
    await set_typing_status(message.peer_id)
    google_sheet = GoogleSheets(calc.type, calc.price, calc.country)
    if re.search(r'DLC', calc.type):
        calc.price = await google_sheet.dlc_price()
    else:
        calc.price = await google_sheet.determine_price()
        await extract_prices(calc.price)
    await send_prices(message)
    logger.info(f'waiting_price({message.peer_id})')
    await bot.state_dispenser.set(message.peer_id, calc_states.waiting_answer)

@cbl.private_message(state=calc_states.waiting_answer)
async def waiting_answer(message: Message):
    if message.text == 'Посчитать ещё':
        await startup_calc(message.peer_id)
        logger.info(f'Калькулятор запущен заново')
        return True
    else:
        await bot.state_dispenser.delete(message.peer_id)
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
            peer_id=message.peer_id,
            message='Нажми кнопку',
            random_id=0,
            keyboard=keyboard
        )
        logger.info(f'send keyboard in {message.peer_id}')
        logger.info(f'({message.peer_id}) вышел из калькулятора.')
        return True


"""SECONDARY FUNCTION"""

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


async def extract_prices(prices_dict: dict) -> bool:
    try:
        global calc
        if 'price_T2P2' in prices_dict:
            calc.T2P2_price = prices_dict['price_T2P2']
            logger.info(f'Get T2P2_price - {calc.T2P2_price}')
        if 'price_T3P3' in prices_dict:
            calc.T3P3_price = prices_dict['price_T3P3']
            logger.info(f'Get T3P3_price - {calc.T3P3_price}')
        if 'price_P2' in prices_dict:
            calc.P2_price = prices_dict['price_P2']
            logger.info(f'Get P2_price - {calc.P2_price}')
        if 'price_P3' in prices_dict:
            calc.P3_price = prices_dict['price_P3']
            logger.info(f'Get P3_price - {calc.P3_price}')
        return True
    except Exception as e:
        logger.error(f'Error extract prices: {e}')
        return False

async def send_prices(message: Message) -> bool:
    try:
        global calc
        text = 'Цены:\n\n'
        text += f'Т2/П2: {calc.T2P2_price}р\n' if calc.T2P2_price is not None else ' '
        text += f'Т3/П3: {calc.T3P3_price}р\n' if calc.T3P3_price is not None else ' '
        text += f'П2: {calc.P2_price}р\n' if calc.P2_price is not None else ' '
        text += f'П3: {calc.P3_price}р\n' if calc.P3_price is not None else''

        if calc.type == 'DLC_PS4':
            text += f'Т3: {calc.price}р\n'
            text += f'П3: {calc.price}р'

        if calc.type == 'DLC_PS5':
            text += f'П3: {calc.price}р'

        keyboard = (Keyboard(one_time=True, inline=False)
                    .add(Text('Посчитать ещё'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('Выйти'), color=KeyboardButtonColor.NEGATIVE)
                    ).get_json()

        await message.answer(message=text, keyboard=keyboard, random_id=0)
        return True
    except Exception as e:
        logger.error(f'Error send prices: {e}')
        return False









