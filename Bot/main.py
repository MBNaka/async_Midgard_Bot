import logging
from vkbottle.bot import Bot
from handlers import labelers
from loader import bot
from utils.check_polls import  auto_start_check_polls
from handlers.echo import send_messages

# Логирование
logging.getLogger("vkbottle").setLevel(logging.INFO)
logging.basicConfig(
    filename='files/bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

try:
    for custom_labeler in labelers:
        bot.labeler.load(custom_labeler)
    logger.info("Custom labelers loaded")
except Exception as e:
    logger.error(f"Error loading custom labelers: {e}")
    exit(1)

@bot.loop_wrapper.interval(seconds=3600)
async def check_polls():
    await auto_start_check_polls()
@bot.loop_wrapper.interval(seconds=60)
async def send_sech_messages():
    await send_messages()

if __name__ == "__main__":
    logger.info("Bot started")
    bot.loop_wrapper.on_startup.append(check_polls())
    bot.run_forever()
    logger.info("Bot stopped")
