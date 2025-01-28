import logging
from vkbottle.bot import Bot
from vkbottle import API
from config import API_KEY, USER_API_KEY, USER_API_KEY_0

logger = logging.getLogger(__name__)

try:
    bot = Bot(token=API_KEY)
    user_bot = API(token=USER_API_KEY)
    midg_user_bot = API(token=USER_API_KEY)
    adm_user_bot = API(token=USER_API_KEY_0)

    logger.info("Bot starting...")
except Exception as e:
    logger.error(e)
    exit(1)