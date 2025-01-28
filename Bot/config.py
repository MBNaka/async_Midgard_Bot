import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='files/.env')

API_KEY = os.getenv("TEST_API_KEY")
USER_API_KEY = os.getenv("USER_API_KEY")
USER_API_KEY_0 = os.getenv("USER_API_KEY_0")
OWNER_ID_1 = os.getenv("OWNER_ID_1")
OWNER_ID_2 = os.getenv("OWNER_ID_2")
POLL_PEER_ID = os.getenv("POLL_PEER_ID")
USER_POLL_PEER_ID = os.getenv("USER_POLL_PEER_ID")
FLOOD_PEER_ID = os.getenv("FLOOD_PEER_ID")
GROUP_ID = os.getenv("GROUP_ID")
SHEET_LINK = os.getenv("SHEET_LINK")
COUNT = 50  # Количество последних сообщений

owner_ids = [OWNER_ID_1, OWNER_ID_2, GROUP_ID]
admin_ids = [OWNER_ID_1, OWNER_ID_2]
ignored_chats = [POLL_PEER_ID, FLOOD_PEER_ID]

poll_commands = ['create_poll', 'send_poll', 'fix_poll', 'cancel_poll']



