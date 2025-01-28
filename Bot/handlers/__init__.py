from . import user_messages
from . import admin_messages
from . import echo
from utils.manual_create_poll import bl
from utils.fix_create_poll import fbl
from utils.calc import cbl

labelers = [admin_messages.bl, echo.ebl, user_messages.bl, bl, fbl, cbl]