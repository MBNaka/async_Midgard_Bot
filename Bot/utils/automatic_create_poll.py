'''
TODO:
Настроить lib ps4store на хостинге
Продумать создание изображения
'''
from vkbottle.bot import Message
from vkbottle import Keyboard, KeyboardButtonColor, Text
from psstore4ru.core.scraping_routines.game_page import PS4Game
from utils.google_sheets import GoogleSheets, save_poll
from config import OWNER_ID_2, POLL_PEER_ID
from loader import bot, midg_user_bot, adm_user_bot
import logging
import json

logging.basicConfig(filename='files/bot.log', level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

auto_create_poll_commands = ['auto_send_poll', 'auto_fix_poll', 'auto_cancel_poll']
'''
CLASS DETERMINE
'''
class Determine:
    def __init__(self, poll):
        self.poll = poll

    def __del__(self):
        logger.info(f'Delete poll - {self.poll.title}')

    async def _ps_type(self, data) -> str:
        support = data['misc'].get('supported')
        if support == 'PS5':
            self.poll.ps_type = 'PS5'
        else:
            self.poll.ps_type = 'PS4, PS5'
        logger.info(f'Get ps type - {self.poll.ps_type}')

    async def _description(self, data) -> bool:
        audio = data.get('audio')
        subtitles = data.get('subtitles')
        preorder = data['misc'].get('category')
        if preorder == 'Предзаказ':
            release_date = data.get('release_date')
            self.poll.description = f'Предзаказ на {release_date}'
        else:
            for lang in audio:
                if lang == 'Russian' or lang == 'Русский':

                    self.poll.description = 'русская озвучка'
                    logger.info(f'Get audio - {self.poll.description}')
                    return
                elif lang == 'English' or lang == 'Английский':
                    self.poll.description = '-английский язык'
                    logger.info(f'Get audio - {self.poll.description}')

            for lang in subtitles:
                if lang == 'Russian' or lang == 'Русский':
                    self.poll.description = 'русские субтитры'
                    logger.info(f'Get subtitles - {self.poll.description}')
                    return
                elif (lang == 'English' or lang == 'Английский') and self.poll.description is not None:
                    self.poll.description = 'английские субтитры'
                logger.info(f'Get subtitles - {self.poll.description}')
        if self.poll.description is None:
            self.poll.description = '-не содержит основную игру'
            self.poll.warning = True
            logger.info(f'Get description - {self.poll.description}')

    async def _country(self, data):
        country = data.get('link').split('-')[1].split('/')[0]
        self.poll.country = country
        logger.info(f'Get country - {self.poll.country}')
        return

    async def _prices(self):
        google_sheet = GoogleSheets(self.poll.ps_type, self.poll.price, self.poll.country)
        if self.poll.dlc:
            self.poll.price = await google_sheet.dlc_price()
            return
        prices_dict = await google_sheet.determine_price()# It may contain: T2P2_price, T3P3_price, P2_price, P3_price
        self.poll.price = prices_dict

        logger.info(f'Determine prices - {prices_dict}')
        if 'price_T2P2' in prices_dict:
            self.poll.T2P2_price = prices_dict['price_T2P2']
            logger.info(f'Get T2P2_price - {self.poll.T2P2_price}')
        if 'price_T3P3' in prices_dict:
            self.poll.T3P3_price = prices_dict['price_T3P3']
            logger.info(f'Get T3P3_price - {self.poll.T3P3_price}')
        if 'price_P2' in prices_dict:
            self.poll.P2_price = prices_dict['price_P2']
            logger.info(f'Get P2_price - {self.poll.P2_price}')
        if 'price_P3' in prices_dict:
            self.poll.P3_price = prices_dict['price_P3']
            logger.info(f'Get P3_price - {self.poll.P3_price}')
        return

    async def _picture(self, event):
        try:
            try:
                attachment = event['object']['message']['attachments'][0]
                self.poll.step = 'picture'
            except Exception as e:
                logger.error(f'Picture not not found in attachment, {e}')
            if self.poll.step != 'picture':
                message = 'Ошибка. Отправь ссылку вместе с картинкой'
                await bot.api.messages.send(peer_id=event['object']['message']['from_id'],
                                            message=message, random_id=0)
                self.poll.step = 'picture'
                logger.info(f'Step - {self.poll.step}')
                return

            photo = attachment['photo']

            photo_id = photo['id']
            owner_id = photo['owner_id']
            access_key = photo['access_key']

            self.poll.picture = f'photo{owner_id}_{photo_id}_{access_key}'
            logger.info(f'Success save picture - {self.poll.picture}')
            self.poll.step = 'build_poll'
            return
        except Exception as e:
            logger.error(f'Picture not found, {e}')
            pass

'''
CLASS FOR THE CREATE POLL
'''
class AutoCreatePoll():
    class Poll:
        def __init__(self, step, title=None, description=None, picture=None, poll=None,
                     ps_type=None, country=None, dlc=None, price=None,
                     keyboard=None, message=None, attachments=None,
                     T2P2_price=None, T3P3_price=None, P2_price=None, P3_price=None):
            self.step = step
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
            self.T2P2_price = T2P2_price
            self.T3P3_price = T3P3_price
            self.P2_price = P2_price
            self.P3_price = P3_price
            self.filling_method = None
            self.warning = None

    def __init__(self):
        self.poll = None
        self.determine = None

    async def determine_way(self, event, link: bool=False):
        try:
            payload = event['object']['message']['payload']
            payload = json.loads(payload)
            command = payload['command']
            logger.info(f'Command - {command}')
        except Exception as e:
            logger.error("Payload not found")
            command = None

        if link:
            message = 'Секунду...'
            await self.send_message(event['object']['message']['from_id'], message)
            self.poll = self.Poll(step='link')
            self.determine = Determine(self.poll)

        if command == 'create_poll':
            message = 'Отправь ссылку, а также прикрепи фото:'
            await self.send_message(event['object']['message']['peer_id'], message)
            logger.info(f'create_poll.send_message into {event["object"]["message"]["peer_id"]}')
            self.poll = self.Poll(step='link')
            self.determine = Determine(self.poll)

        elif self.poll.step == 'link':
            logger.info('Start create')
            await self.create(event)

        elif self.poll.step == 'picture':
            await self.determine._picture(event)

        if self.poll.step == 'build_poll':
            logger.info(f'Step - {self.poll.step}')
            await self.build_poll(event)
            await self.convert_to_msg(event)

    async def create(self, event):
        message = event['object']['message']['text']
        if message.startswith('https://store.playstation.com'):
            data = await self.fetch_data_from_psstore(message)
            data = json.loads(data)
            logger.info('take data from ps store')
            self.poll.title = data.get('title')
            self.poll.price = data.get('final_price')
            logger.info(f'Get title - {self.poll.title}, price - {self.poll.price}')

            await self.determine._ps_type(data)
            await self.determine._description(data)
            await self.determine._country(data)
            await self.determine._prices()
            await self.determine._picture(event)
        else:
            poll = self.Poll(title=message)

    async def fetch_data_from_psstore(self, link):
        game = PS4Game(link)
        data = game.as_json()
        print(data)
        logger.info(f'Fetch data from link - {link}')
        return data

    async def send_message(self, peer_id, message, payload=None, attachments=None, keyboard=None):
        await bot.api.messages.send(
            peer_id=peer_id,
            message=message,
            random_id=0,
            attachment=attachments,
            keyboard=keyboard,
            payload=payload
        )

    async def build_poll(self, event):
        question = 'Бронь'
        answers = []
        if self.poll.dlc is not None:
            if self.poll.ps_type == 'PS5':
                answers.append(f'П3 - {self.poll.price}р')
            elif self.poll.ps_type == 'PS4, PS5':
                answers.append(f'Т3 - {self.poll.price}р')
                answers.append(f'П3 - {self.poll.price}р')
        else:
            if self.poll.T2P2_price is not None:
                answers.append(f'Т2/П2 - {self.poll.T2P2_price}р')
            if self.poll.T3P3_price is not None:
                answers.append(f'Т3 - {self.poll.T3P3_price}р')
                answers.append(f'П3 - {self.poll.T3P3_price}р')
            if self.poll.P2_price is not None:
                answers.append(f'П2 - {self.poll.P2_price}р')
            if self.poll.P3_price is not None:
                answers.append(f'П3 - {self.poll.P3_price}р')
        answers.append('Просто кнопка')
        logger.info(f'answers - {answers}')

        result = await midg_user_bot.polls.create(
            question=question,
            add_answers=json.dumps(answers),
            owner_id=OWNER_ID_2
        )

        poll_id = result.id
        self.poll.poll = f'poll{OWNER_ID_2}_{poll_id}'
        logger.info(f'Success build poll - {self.poll.poll}')
        return


    async def convert_to_msg(self, event):
        if self.poll.warning is True:
            message = ('&#9888; ВНИМАНИЕ! Проверить описание и цены, если неправильно - исправить через меню! &#9888;\n\n'
                       f'{self.poll.title}&#128293;\n\n'
                       f'{self.poll.description}\n\n'
                       'Желающие собрать бронируем места в опросе &#128071;\n\n'
                       'Если вы не готовы купить позицию, не голосуйте!'
                       )
        else:
            message = (f'{self.poll.title}&#128293;\n\n'
                       f'{self.poll.description}\n\n'
                       'Желающие собрать бронируем места в опросе &#128071;\n\n'
                       'Если вы не готовы купить позицию, не голосуйте!'
                       )
        attachments =  f"{self.poll.picture},{self.poll.poll}"
        keyboard = (
            Keyboard(one_time=True, inline=False)
            .add(Text('Отправить', payload={"command": "auto_send_poll"}), color=KeyboardButtonColor.POSITIVE)
            .row()
            .add(Text('Исправить', payload={"command": "auto_fix_poll"}), color=KeyboardButtonColor.PRIMARY)
            .row()
            .add(Text('Отмена', payload={"command": "auto_cancel_poll"}), color=KeyboardButtonColor.NEGATIVE)
        ).get_json()
        await self.send_message(event['object']['message']['peer_id'], message, attachments=attachments, keyboard=keyboard)
        logger.info(f'Success pre_send poll to {event["object"]["message"]["peer_id"]}. title:{self.poll.title}')

    async def send_poll(self, peer_id: int = POLL_PEER_ID):
        message = (f'{self.poll.title}&#128293;\n\n'
                   f'{self.poll.description}\n\n'
                   'Желающие собрать бронируем места в опросе &#128071;\n\n'
                   'Если вы не готовы купить позицию, не голосуйте!'
                   )
        attachments = f"{self.poll.picture},{self.poll.poll}"
        success = await save_poll(self.poll)
        await self.add_vote()
        await self.send_message(peer_id=peer_id, message=message, attachments=attachments)
        if success:
            logger.info(f'Success send and save poll to {peer_id}. title:{self.poll.title}')
        else:
            logger.error(f'Error send and save poll to {peer_id}. title:{self.poll.title}.')

    async def get_poll(self):
        logger.info('Return automatic create poll')
        return self.poll

    async def add_vote(self) -> bool:
        try:
            poll_id = int(self.poll.poll.split('_')[1])
            result = await midg_user_bot.polls.get_by_id(poll_id)
            answer_ids = result.answers
            for answer in answer_ids:
                if answer.text == 'Просто кнопка':
                    answer_id = answer.id
            try:
                await midg_user_bot.polls.add_vote(answer_id, poll_id)
            except:
                pass
            try:
                await adm_user_bot.polls.add_vote( answer_id, poll_id)
            except:
                pass
            logger.info('Success add vote')
            return True
        except Exception as e:
            logger.error(f'Error get add_vote - {e}')
            return False