from vkbottle.bot import Message, BotLabeler
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup, GroupEventType
from utils.google_sheets import save_poll, connect_bd
from vkbottle.dispatch.rules import ABCRule
from config import OWNER_ID_1, OWNER_ID_2, GROUP_ID, POLL_PEER_ID, admin_ids
from loader import midg_user_bot, bot

import datetime
import re
import json
import asyncio
import functools
import logging

# todo: резализовать добавление статистики

logging.basicConfig(filename='files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_every(interval: int):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            while True:
                await func(*args, **kwargs)
                await asyncio.sleep(interval)

        return wrapper

    return decorator


async def check_votes(poll_id: int, type: str, n: int) -> bool or dict:
    try:
        poll = await midg_user_bot.polls.get_by_id(owner_id=OWNER_ID_2, poll_id=poll_id)
        answers = poll.answers  # Используем точечную нотацию

        answer_votes = {answer.text: answer.votes for answer in answers}

        if type == 'PS4, PS5':
            t2p2_value = answers[0].votes
            t3_value = answers[1].votes
            p3_value = answers[2].votes
            if (t2p2_value >= n and t3_value >= n and p3_value >= 2 * n) or \
                    (t2p2_value >= n and t3_value >= 2 * n and p3_value >= n):
                return True
            return {'Т2/П2': t2p2_value, 'Т3': t3_value, 'П3': p3_value}

        elif type == 'PS5':
            p2_value = answers[0].votes
            p3_value = answers[1].votes
            if p2_value >= n and p3_value >= 2 * n:
                return True
            return {'П2': p2_value, 'П3': p3_value}

        elif type == 'DLC_PS4':
            t3_value = answers[0].votes
            p3_value = answers[1].votes
            if (p3_value >= 2 * n and t3_value >= n) or \
                    (t3_value >= 2 * n and p3_value >= n):
                return True
            return {'Т3': t3_value, 'П3': p3_value}

        elif type == 'DLC_PS5':
            p3_value = answers[0].votes
            if p3_value >= 2 * n:
                return True
            return {'П3': p3_value}

        elif type == 'PS_PLUS_PS4':
            p2_value = answers[0].votes
            t3_value = answers[1].votes
            p3_value = answers[2].votes
            if (p2_value >= n and t3_value >= 2 * n and p3_value >= n) or \
                    (p2_value >= n and t3_value >= n and p3_value >= 2 * n):
                return True
            return {'П2': p2_value, 'Т3': t3_value, 'П3': p3_value}

        elif type == 'PS_PLUS_PS5':
            p2_value = answers[0].votes
            p3_value = answers[1].votes
            if p2_value >= n and p3_value >= 2 * n:
                return True
            return {'П2': p2_value, 'П3': p3_value}

    except Exception as e:
        logger.error(f'Error in check_votes: {e}')
        return False


async def get_voters(poll_id: int) -> dict:
    try:
        poll = await midg_user_bot.polls.get_by_id(owner_id=OWNER_ID_2, poll_id=poll_id)
        answers = poll.answers

        voters = {}

        for answer in answers:
            if answer.text != 'Просто кнопка':
                print(poll_id)
                response = await midg_user_bot.polls.get_voters(poll_id=poll_id, answer_ids=[answer.id])
                voter_info = response[0]
                voters_ids = voter_info.users.items
                voters[answer.text] = voters_ids

        return voters

    except Exception as e:
        logger.error(f'Error in get_voters: {e}')
        return {}


async def check_polls():
    logger.info('Starting check_polls')
    worksheet = await connect_bd()
    if worksheet is None:
        return -1
    records = worksheet.get_all_records()

    for i, record in enumerate(records, start=2):
        poll_id = record['POLL_ID']
        type = record['TYPE']
        multiplier = record['MULTIPLIER']
        title = record['TITLE']

        answer = await check_votes(poll_id, type, multiplier)
        answer = await check_votes(poll_id, type, multiplier)
        answer = await check_votes(poll_id, type, multiplier)
        answer = await check_votes(poll_id, type, multiplier)
        answer = await check_votes(poll_id, type, multiplier)
        answer = await check_votes(poll_id, type, multiplier)
        answer = await check_votes(poll_id, type, multiplier)

        if answer is True:
            logger.info(f'Poll (poll_id:{poll_id}, title: {title}) is completed')
            voters = await get_voters(poll_id)

            message = f'Можно собрать игру: {title}.\n'
            for answer_text, voters_ids in voters.items():
                message += f"{answer_text}:\n"
                for voter_id in voters_ids:
                    user_info = await midg_user_bot.users.get(user_ids=voter_id)
                    first_name = user_info[0].first_name
                    last_name = user_info[0].last_name
                    message += f"*id{voter_id} ({first_name} {last_name})\n"
            for peer_id in admin_ids:
                try:
                    await bot.api.messages.send(
                        peer_id=peer_id,
                        message=message,
                        random_id=0
                    )
                except Exception as e:
                    pass

            # game = await add_game(title, self.poll.ps_type, self.poll.price)

            current_value = int(worksheet.cell(i, 6).value)
            new_value = current_value + 1
            worksheet.update_cell(i, 6, new_value)
            logger.info(f'Poll {poll_id}: multiplier updated to {new_value}')
        else:
            logger.info(f'Poll (poll_id:{poll_id}, title: {title}) is not completed')
            worksheet.update_cell(i, 5, str(answer))

    logger.info('Ending check_polls')

async def auto_start_check_polls():
    logger.info("auto_start_check_polls started.")
    try:
        await check_polls()
    except Exception as e:
        logger.error(f"Error in auto_start_check_polls: {e}")
        for peer_id in admin_ids:
            try:
                await bot.api.messages.send(
                    peer_id=peer_id,
                    message=f"Ошибка в авто-проверке опросов: {e}",
                    random_id=0,
                )
            except Exception as nested_e:
                logger.error(f"Error sending error message to admin {peer_id}: {nested_e}")

