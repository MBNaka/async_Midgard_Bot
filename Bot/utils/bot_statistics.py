import logging
from audioop import avgpp
from venv import logger

from vkbottle.bot import BotLabeler, Message
from vkbottle import Keyboard, KeyboardButtonColor, Text, OpenLink
from utils.sql_statistics import add_sale, add_inquiry, add_user_time, get_summary_stats, get_inquiries_stats, get_avg_user_time, get_top_games
from config import admin_ids
from loader import bot
logging.basicConfig(filename='files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

async def add_game(_title: str, _platform: str, prices_dict: dict, quantily: int=1) -> bool:
    try:
        revenue = 0
        keys_to_check = ['price_T2P2', 'price_T3P3', 'price_P2', 'price_P3']
        for key in keys_to_check:
            if key in prices_dict:
                revenue += prices_dict[key]
                logger.info(f'{key}: {prices_dict[key]}')
        await add_sale(_title, _platform, quantily, revenue)
        logger.info(f'{_title}: {revenue}')
        return True
    except Exception as e:
        logger.error(f'bot_statistics_add_game: {e}')
        return False

async def add_request(user_time: int) -> bool:
    await add_inquiry()
    await add_user_time(user_time)

async def send_report(peer_id, start_date=None, end_date=None):
    try:
        summary = await get_summary_stats(start_date, end_date)
        inquiries = await get_inquiries_stats(start_date, end_date)
        avg_user_time = await get_avg_user_time(start_date, end_date)

        report = f'Статистика с {start_date} по {end_date}\n'
        report += f"Общее количество продаж: {summary['total_sales']}\n"
        report += f"Общая выручка: {summary['total_revenue']} ₽\n"
        report += f"Обращений за помощью: {inquiries}\n"
        report += f"Среднее время работы с пользователем: {round(avg_user_time)} мин.\n"
        report += "Топ 5 популярных игр:\n"
        count = 0
        for game, sales in summary["top_games"]:
            report += f"{count+1}. {game}: {sales} шт.\n"
            count += 1

        logger.info('Report is builded')
        return report
    except Exception as e:
        logger.error(f'bot_statistics_report: {e}')
        return 'Ошибка при формировании отчета'


