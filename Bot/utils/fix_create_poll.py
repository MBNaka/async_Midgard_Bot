from vkbottle.bot import Message, BotLabeler
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup
from utils.google_sheets import GoogleSheets
from vkbottle.dispatch.rules import ABCRule
from config import OWNER_ID_1, OWNER_ID_2, POLL_PEER_ID, admin_ids
from loader import midg_user_bot, bot

import re
import json
import logging

logging.basicConfig(filename='files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FromAdminRule(ABCRule[Message]):
    async def check(self, message: Message) -> bool:
        return str(message.from_id) in admin_ids

fbl = BotLabeler()
fbl.auto_rules = [FromAdminRule()]

poll = None
method = None

class states(BaseStateGroup):
    keyboard =          0
    request_title =     1
    req_description =   2
    image =             3
    type =              4
    DLC_or_PS_PLUS =    5
    country =           6
    price =             7
    determine_method =  8


"""MAIN FUNCTION"""

async def keyboard(peer_id: int) -> bool:
    try:
        keyboard = (Keyboard(one_time=True)
                    .add(Text('Название'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('Описание'), color=KeyboardButtonColor.PRIMARY)
                    .row()
                    .add(Text('Картинка'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('Тип опроса'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('Цена'), color=KeyboardButtonColor.PRIMARY)
                    .row()
                    .add(Text('Вернуться'), color=KeyboardButtonColor.NEGATIVE)
                    )
        message = 'Выбери, что ты хочешь изменить или вернись назад при помощи кнопки'
        await bot.api.messages.send(peer_id=peer_id, message=message, random_id=0, keyboard=keyboard)
        logger.info(f'Отправка клавиатуры в чат к {peer_id}')
        return True
    except Exception as e:
        logger.error(f'Ошибка при отправке клавиатуры: {e}')
        return False

async def _send_keyboard(fixpoll, automatic_method: bool, peer_id: int) -> bool:
    try:
        global poll, method
        method = 'auto' if automatic_method is True else 'manual'

        poll = fixpoll
        await keyboard(peer_id)
        return True
    except Exception as e:
        logger.error(f'Ошибка при отправке клавиатуры: {e}')
        return False


"""UTILS FOR FIX"""

@fbl.private_message(lev='Название')
async def _rename_title(message: Message) -> bool:
    await message.answer("Напиши название игры:")
    await bot.state_dispenser.set(message.peer_id, states.request_title)

@fbl.private_message(state=states.request_title)
async def _get_title(message: Message) -> bool:
    global poll
    poll.title = message.text
    await message.answer(f"Название успешно изменено на {poll.title}")
    await keyboard(message.peer_id)
    await bot.state_dispenser.set(message.peer_id, states.keyboard)

@fbl.private_message(lev='Описание')
async def _description(message: Message) -> bool:
    await message.answer("Напиши описание игры:")
    await bot.state_dispenser.set(message.peer_id, states.req_description)

@fbl.private_message(state=states.req_description)
async def _get_description(message: Message) -> bool:
    global poll
    poll.description = message.text
    await message.answer(f"Описание успешно изменено на {poll.description}")
    await keyboard(message.peer_id)
    await bot.state_dispenser.set(message.peer_id, states.keyboard)

@fbl.private_message(lev='Картинка')
async def _image(message: Message) -> bool:
    await message.answer("Отправь картинку:")
    await bot.state_dispenser.set(message.peer_id, states.image)

@fbl.private_message(state=states.image)
async def _get_image(message: Message) -> bool:
    global poll
    picture = message.get_photo_attachments()
    photo = picture[0]
    access_key = photo.access_key
    id = photo.id
    owner_id = photo.owner_id
    poll.picture = f'photo{owner_id}_{id}_{access_key}'
    await message.answer("Картинка успешно изменена")
    await keyboard(message.peer_id)
    await bot.state_dispenser.set(message.peer_id, states.keyboard)

@fbl.private_message(lev='Цена')
async def change_price(message: Message) -> bool:
    keyboard = (Keyboard(one_time=True, inline=False)
                .add(Text('Автоматически'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('Вручную'), color=KeyboardButtonColor.PRIMARY)
                ).get_json()
    await message.answer('Выбери способ заполнения', keyboard=keyboard)
    await bot.state_dispenser.set(message.peer_id, states.determine_method)

@fbl.private_message(lev='Тип опроса')
async def _type(message: Message) -> bool:
    keyboard = (Keyboard(one_time=True, inline=False)
                .add(Text('PS4, PS5'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('PS5'), color=KeyboardButtonColor.PRIMARY)
                .row()
                .add(Text('DLC'), color=KeyboardButtonColor.PRIMARY)
                .add(Text('PS PLUS'), color=KeyboardButtonColor.PRIMARY)
                ).get_json()
    await message.answer("Выбери тип опроса:", keyboard=keyboard)
    await bot.state_dispenser.set(message.peer_id, states.type)

@fbl.private_message(state=states.type)
async def _get_type(message: Message) -> bool:
    global poll
    if message.text == 'PS4, PS5' or 'PS5':
        try:
            poll.ps_type = message.text
            fill = await filling_method_kbrd(message.peer_id)
            await bot.state_dispenser.set(message.peer_id, states.determine_method)
        except Exception as e:
            message.answer("Ошибка. Попробуй ещё раз")
    elif message.text == 'DLC' or 'PS PLUS':
        try:
            poll.ps_type = message.text
            await bot.state_dispenser.set(message.peer_id, states.DLC_or_PS_PLUS)
            keyboard = (Keyboard(one_time=True, inline=False)
                        .add(Text('С Т3 (PS4)'), color=KeyboardButtonColor.PRIMARY)
                        .add(Text('Без Т3 (PS5)'), color=KeyboardButtonColor.PRIMARY)
                        ).get_json()
            await message.answer("Выбери способ заполнения:", keyboard=keyboard)
        except Exception as e:
            await message.answer("Ошибка. Попробуй ещё раз")
            logger.error(f'Ошибка при запросе типа DLC or PS PLUS: {e}')

@fbl.private_message(state=states.DLC_or_PS_PLUS)
async def _dlc_or_ps_plus(message: Message) -> bool:
    global poll
    if message.text == 'С Т3 (PS4)':
        poll.ps_type = 'DLC_PS4' if poll.ps_type == 'DLC' else 'PS_PLUS_PS4'
    if message.text == 'Без Т3 (PS5)':
        poll.ps_type = 'DLC_PS5' if poll.ps_type == 'DLC' else 'PS_PLUS_PS5'

    if poll.ps_type == 'DLC_PS4' or poll.ps_type == 'DLC_PS5':
        await message.answer(f"Тип опроса успешно изменен на {poll.ps_type}")
        fill = await filling_method_kbrd(message.peer_id)
        await bot.state_dispenser.set(message.peer_id, states.price)

    elif poll.ps_type == 'PS_PLUS_PS4' or poll.ps_type == 'PS_PLUS_PS5':
        await message.answer(f"Тип опроса успешно изменен на {poll.ps_type}")
        poll.filling_method = 'Вручную'
        await message.answer('Напиши новую цену для П2: ')
        await bot.state_dispenser.set(message.peer_id, states.price)

@fbl.private_message(state=states.determine_method)
async def _get_price(message: Message) -> bool:
    global poll
    poll.filling_method = message.text
    if not re.search(r'PS_PLUS', poll.ps_type):
        if poll.filling_method == 'Автоматически':
            await message.answer('Напиши цену:')
            await bot.state_dispenser.set(message.peer_id, states.price)
        else:
            poll.filling_method = 'Вручную'
            await message.answer('Напиши новую цену для П2: ')
            await bot.state_dispenser.set(message.peer_id, states.price)

@fbl.private_message(state=states.price)
async def _get_price(message: Message) -> bool:
    if poll.filling_method == 'Автоматически':
        poll.price = message.text
        await set_typing_status(message.peer_id)
        google_sheet = GoogleSheets(poll.ps_type, poll.price, poll.country)
        if re.search(r'DLC', poll.ps_type):
            poll.price = await google_sheet.dlc_price()
            await send_prices(message)
            await create_poll(message)
            await keyboard(message.peer_id)
            await bot.state_dispenser.set(message.peer_id, states.keyboard)
        elif poll.ps_type == 'PS5' or poll.ps_type == 'PS4, PS5':
            poll.price = await google_sheet.determine_price()
            await extract_prices(poll.price)
            await send_prices(message)
            await create_poll(message)
            await keyboard(message.peer_id)
            await bot.state_dispenser.set(message.peer_id, states.keyboard)

    if poll.filling_method == 'Вручную':
        if poll.step is None:
            poll.step = await request_prices(message, poll.step)
        elif poll.step is not None:
            poll.step = await request_prices(message, poll.step)
        if poll.step == 'Done':
            await create_poll(message)
            await keyboard(message.peer_id)
            await bot.state_dispenser.set(message.peer_id, states.keyboard)

@fbl.private_message(lev='Вернуться')
async def _back(message: Message) -> bool:
    global poll
    try:
        await bot.state_dispenser.delete(message.peer_id)
        await send_message(message)
        logger.info(f'Успешное изменение опроса у user {message.peer_id}')
        return True
    except Exception as e:
        logger.error(f'Ошибка при изменении опроса: {e}')
        await message.answer('Произошла ошибка. Напиши "отмена" и попробуй заново')
        return False

@fbl.private_message(state=states.keyboard)
async def _keyboard(message: Message) -> bool:
    await keyboard(message.peer_id)


"""SECONDARY FUNCTIONS"""

async def send_message(message: Message):
    global poll, method
    text = (f'{poll.title}&#128293;\n\n'
               f'{poll.description}\n\n'
               'Желающие собрать бронируем места в опросе &#128071;\n\n'
               'Если вы не готовы купить позицию, не голосуйте!'
               )
    attachments = f"{poll.picture},{poll.poll}"
    keyboard = (
        Keyboard(one_time=True, inline=False)
        .add(Text('Отправить', payload={"command": f"{method}_send_poll"}), color=KeyboardButtonColor.POSITIVE)
        .row()
        .add(Text('Исправить', payload={"command": f"{method}_fix_poll"}), color=KeyboardButtonColor.PRIMARY)
        .row()
        .add(Text('Отмена', payload={"command": f"{method}_cancel_poll"}), color=KeyboardButtonColor.NEGATIVE)
    ).get_json()
    print(attachments)
    await message.answer(message=text, keyboard=keyboard, attachment=attachments)

    logger.info(f'Success pre_send poll to {message.peer_id}. title:{poll.title}')
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
        if poll.ps_type == 'DLC PS5' or poll.ps_type == 'DLC PS4':
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
        if poll.ps_type == 'DLC PS5' or 'DLC PS4':
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
        poll.T2P2_price = None
        poll.P2_price = None
        poll.P3_price = None
        poll.T3P3_price = None
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

async def filling_method_kbrd(peer_id: int) -> bool:
    try:
        keyboard = (Keyboard(one_time=True)
                    .add(Text('Автоматически'), color=KeyboardButtonColor.PRIMARY)
                    .add(Text('Вручную'), color=KeyboardButtonColor.PRIMARY)
                    ).get_json()
        message = 'Выбери способ заполнения:'
        await bot.api.messages.send(peer_id=peer_id, message=message, random_id=0, keyboard=keyboard)
        return True
    except Exception as e:
        logger.error(f'Ошибка при отправке клавиатуры: {e}')
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

async def send_prices(message: Message) -> bool:
    try:
        global poll
        text = 'Цены:\n\n'
        text += f'Т2/П2: {poll.T2P2_price}р\n' if poll.T2P2_price is not None else ' '
        text += f'Т3/П3: {poll.T3P3_price}р\n' if poll.T3P3_price is not None else ' '
        text += f'П2: {poll.P2_price}р\n' if poll.P2_price is not None else ' '
        text += f'П3: {poll.P3_price}р\n' if poll.P3_price is not None else''

        if poll.ps_type == 'DLC_PS4':
            text += f'Т3: {poll.price}р\n'
            text += f'П3: {poll.price}р'

        if poll.ps_type == 'DLC_PS5':
            text += f'П3: {poll.price}р'

        await message.answer(message=text, random_id=0)
        return True
    except Exception as e:
        logger.error(f'Error send prices: {e}')
        return False