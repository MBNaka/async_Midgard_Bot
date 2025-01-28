from oauth2client.service_account import ServiceAccountCredentials
from config import SHEET_LINK, POLL_PEER_ID

import gspread
import datetime
from logging import getLogger

logger = getLogger(__name__)

async def save_poll(poll, peer_id: int = POLL_PEER_ID, msg_id: int = None) -> bool:
    try:
        worksheet = await connect_bd()
        title = poll.title
        poll_id = int(poll.poll.split('_')[1])
        type = poll.ps_type
        price = poll.price
        positions = await determine_position(type)
        date = datetime.datetime.now()
        date = date.strftime('%d.%m.%Y')
        multiplier = 1
        data = [poll_id, title, type,  str(price), str(positions), multiplier, date, msg_id]
        print(data)
        worksheet.append_row(data)
        logger.info(f'Poll with this info has been added: {data}')
    except Exception as e:
        logger.error(f'Error while adding poll: {e}. {data}')
        return False
    return True

async def determine_position(type):
    if type == 'PS4, PS5':
        positions = {'Т2/П2': 0, 'Т3': 0, 'П3': 0}
    elif type == 'PS5':
        positions = {'П2': 0, 'П3': 0}
    elif type == 'DLC_PS4':
        positions = {'Т3': 0, 'П3': 0}
    elif type == 'DLC_PS5':
        positions = {'П3': 0}
    elif type == 'PS_PLUS_PS4':
        positions = {'П2': 0, 'Т3': 0, 'П3': 0}
    elif type == 'PS_PLUS_PS5':
        positions = {'П2': 0, 'П3': 0}
    return positions

async def connect_bd():
    credentials = ServiceAccountCredentials.from_json_keyfile_name('files/credentials.json',
                                                                   ['https://spreadsheets.google.com/feeds',
                                                                    'https://www.googleapis.com/auth/drive'])
    client = gspread.authorize(credentials)
    try:
        sheet = client.open_by_url(SHEET_LINK)
        worksheet = sheet.get_worksheet(5)
        return worksheet
    except gspread.exceptions.APIError as e:
        print(f"API error: {e}")
        return None
    except Exception as e:
        print(f"Other error: {e}")
        return None

class GoogleSheets():
    def __init__(self, type: str, price: str, country: str):
        self.type = type
        self.price = price
        self.country = country

    async def round_to_nearest(self, value: float, base=50) -> int:
        return base * round(value / base)

    async def connect(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_name('files/credentials.json',
                                                                   ['https://spreadsheets.google.com/feeds',
                                                                    'https://www.googleapis.com/auth/drive'])
        client = gspread.authorize(credentials)
        sheet = client.open_by_url(SHEET_LINK)
        worksheet = sheet.get_worksheet(4) # calc
        return worksheet

    async def dlc_price(self) -> int:
        worksheet = await self.connect()
        if self.country == 'tr' or self.country == 'Турция' or self.country == 'Turkey':
            row = 4
        elif self.country == 'ua' or self.country == 'Украина' or self.country == 'Ukraine':
            row = 11
        if self.type == 'DLC_PS5':
            num = 2
        elif self.type == 'DLC_PS4':
            num = 3
        else:
            return 'ОШИБКА'
        worksheet.update_cell(row, 1, self.price)
        dlc_price = await self.round_to_nearest(float(worksheet.acell(f'C{row}').value.replace(',', '.'))/num)
        return dlc_price

    async def determine_price(self) -> dict:
        prices_dict = {}
        worksheet = await self.connect()

        if self.country == 'tr' or self.country == 'Турция' or self.country == 'Turkey':
            row = 4
        elif self.country == 'ua' or self.country == 'Украина' or self.country == 'Ukraine':
            row = 11

        worksheet.update_cell(row, 1, self.price)
        logger.info(f'type: {self.type}')
        if self.type == 'PS5':
            prices_dict['price_P2'] = await self.round_to_nearest(float(worksheet.acell(f'F{row}').value.replace(',', '.')))
            prices_dict['price_P3'] = await self.round_to_nearest(float(worksheet.acell(f'D{row}').value.replace(',', '.')))
        elif self.type == 'PS4, PS5':
            prices_dict['price_T2P2'] = await self.round_to_nearest(float(worksheet.acell(f'G{row}').value.replace(',', '.')))
            prices_dict['price_T3P3'] = await self.round_to_nearest(float(worksheet.acell(f'H{row}').value.replace(',', '.')))
        return prices_dict