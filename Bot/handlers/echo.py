import asyncio
import logging
from datetime import datetime
from vkbottle.bot import Bot, Message, BotLabeler
from vkbottle import Keyboard, KeyboardButtonColor, Text, BaseStateGroup
from utils.echo import load_data, save_data, format_date, calculate_next_date
from loader import bot

logging.basicConfig(
    filename='files/bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ebl = BotLabeler()


class EchoStates(BaseStateGroup):
    adding_message = "adding_message"
    adding_date = "adding_date"
    adding_repeat = "adding_repeat"
    delete_message = "delete_message"


# Клавиатура главного меню
def main_keyboard():
    return (Keyboard(one_time=True)
            .add(Text("Добавить сообщение"), color=KeyboardButtonColor.POSITIVE)
            .add(Text("Список сообщений"), color=KeyboardButtonColor.PRIMARY)
            .row()
            .add(Text("Удалить сообщение"), color=KeyboardButtonColor.NEGATIVE)
            .add(Text("Админпанель"), color=KeyboardButtonColor.PRIMARY)
            ).get_json()


@ebl.private_message(text="Эхо")
async def echo(message: Message):
    logger.info(f"Пользователь {message.from_id} открыл главное меню.")
    message_text = "Тут ты можешь управлять эхо-сообщениями, которые отправляет бот"
    await message.reply(message_text, keyboard=main_keyboard())


# Добавление сообщения
@ebl.private_message(text="Добавить сообщение")
async def start_add_message(message: Message):
    logger.info(f"Пользователь {message.from_id} начал добавление сообщения.")
    await message.reply("Отправьте текст сообщения.", keyboard=Keyboard(inline=True).add(Text("Отмена")).get_json())
    await bot.state_dispenser.set(message.peer_id, EchoStates.adding_message)

@ebl.private_message(state=EchoStates.adding_message)
async def add_message_step_1(message: Message):
    text = message.text
    logger.info(f"Пользователь {message.from_id} ввёл текст сообщения: {text}")

    # Убедимся, что текст сохраняется в payload
    payload = {"text": text}
    logger.debug(f"Устанавливаем payload для пользователя {message.peer_id}: {payload}")

    await bot.state_dispenser.set(message.peer_id, EchoStates.adding_date, payload=payload)

    await message.reply("Введите дату и время в формате: дд.мм.гггг чч:мм")

@ebl.private_message(state=EchoStates.adding_date)
async def add_message_step_2(message: Message):
    send_date = format_date(message.text)
    if not send_date:
        logger.warning(f"Пользователь {message.from_id} ввёл неверный формат даты: {message.text}")
        await message.reply("Неверный формат даты. Попробуйте ещё раз: дд.мм.гггг чч:мм")
        return

    # Проверяем текущее состояние и payload
    current_state = await bot.state_dispenser.get(message.peer_id)
    payload = current_state.payload if current_state and current_state.payload else {}
    logger.debug(f"Текущий payload для {message.peer_id} перед обновлением: {payload}")

    # Добавляем дату в payload
    payload["date"] = send_date
    await bot.state_dispenser.set(message.peer_id, EchoStates.adding_repeat, payload=payload)

    await message.reply("Введите повторение (никогда, ежедневно, ежемесячно, ежегодно):")

@ebl.private_message(state=EchoStates.adding_repeat)
async def add_message_step_3(message: Message):
    repeat = message.text.lower()
    if repeat not in ["никогда", "ежедневно", "ежемесячно", "ежегодно"]:
        logger.warning(f"Пользователь {message.from_id} ввёл неверный тип повторения: {repeat}")
        await message.reply("Неверный тип повторения. Используйте: никогда, ежедневно, ежемесячно, ежегодно.")
        return

    current_state = await bot.state_dispenser.get(message.peer_id)
    payload = current_state.payload if current_state and current_state.payload else {}

    # Извлечение текста и даты
    nested_payload = payload.get("payload")
    text_payload = nested_payload.get("payload")
    text = text_payload.get("text")
    date = nested_payload.get("date")

    logger.debug(f"Полученный payload для пользователя {message.peer_id}: {payload}")

    if not text:
        logger.error(f"В payload отсутствует ключ 'text' для пользователя {message.peer_id}.")
        await message.reply("Произошла ошибка. Попробуйте начать добавление сообщения заново.")
        await bot.state_dispenser.delete(message.peer_id)
        return

    if not date:
        logger.error(f"В payload отсутствует ключ 'date' для пользователя {message.peer_id}.")
        await message.reply("Произошла ошибка. Попробуйте начать добавление сообщения заново.")
        await bot.state_dispenser.delete(message.peer_id)
        return

    chat_id = "2000000001"  # ID чата
    data = load_data()

    if chat_id not in data:
        data[chat_id] = []

    # Сохранение сообщения
    data[chat_id].append({
        "text": text,
        "date": date.strftime("%d.%m.%Y %H:%M"),
        "repeat": repeat
    })
    save_data(data)

    await bot.state_dispenser.delete(message.peer_id)

    logger.info(f"Сообщение добавлено в чат {chat_id}: {text} с датой {date} и повторением {repeat}")
    await message.reply("Сообщение добавлено!", keyboard=main_keyboard())

# Список сообщений
@ebl.private_message(text="Список сообщений")
async def list_messages(message: Message):
    user_id = str(message.from_id)
    data = load_data()
    chat_id = "2000000001"  # ID чата
    if chat_id not in data:
        logger.info(f"Пользователь {user_id} запросил список сообщений, но у него нет сохранённых сообщений.")
        await message.reply("У вас нет сохранённых сообщений.", keyboard=main_keyboard())
        return

    reply = "\n".join(
        f"{i + 1}. {msg['text'][:30]}... | {msg['date']} | {msg['repeat']}"
        for i, msg in enumerate(data[chat_id])
    )
    logger.info(f"Пользователь {user_id} запросил список сообщений. Отправлено {len(data[chat_id])} сообщений.")
    await message.reply(f"Ваши сообщения:\n{reply}\n\nДля подробностей введите индекс сообщения.",
                        keyboard=main_keyboard())


# Подробности сообщения
@ebl.private_message(payload_contains={"action": "details"})
async def message_details(message: Message):
    index = int(message.payload["index"])
    user_id = str(message.from_id)
    data = load_data()

    if user_id not in data or not data[user_id] or index < 1 or index > len(data[user_id]):
        logger.warning(f"Пользователь {user_id} запросил несуществующее сообщение с индексом {index}.")
        await message.reply("Сообщение с таким номером не найдено.", keyboard=main_keyboard())
        return

    msg = data[user_id][index - 1]
    logger.info(f"Пользователь {user_id} запросил сообщение #{index}: {msg['text']}")
    await message.reply(
        f"Сообщение #{index}:\n\nТекст: {msg['text']}\nДата: {msg['date']}\nПовторение: {msg['repeat']}",
        keyboard=main_keyboard())


# Удаление сообщения
@ebl.private_message(text="Удалить сообщение")
async def delete_message_start(message: Message):
    logger.info(f"Пользователь {message.from_id} начал процесс удаления сообщения.")
    await message.reply("Введите номер сообщения для удаления.",
                        keyboard=Keyboard(inline=True).add(Text("Отмена")).get_json())
    await bot.state_dispenser.set(message.peer_id, EchoStates.delete_message)


@ebl.private_message(state=EchoStates.delete_message)
async def delete_message(message: Message):
    index = int(message.text)
    user_id = str(message.from_id)
    data = load_data()
    chat_id = '2000000001'

    if user_id not in data or not data[user_id] or index < 1 or index > len(data[chat_id]):
        logger.warning(f"Пользователь {user_id} попытался удалить несуществующее сообщение с индексом {index}.")
        await message.reply("Сообщение с таким номером не найдено.", keyboard=main_keyboard())
        await bot.state_dispenser.delete(message.peer_id)
        return

    deleted = data[chat_id].pop(index - 1)
    save_data(data)
    logger.info(f"Пользователь {user_id} удалил сообщение с текстом: {deleted['text'][:30]}")
    await message.reply(f"Сообщение удалено: {deleted['text'][:30]}...", keyboard=main_keyboard())
    await bot.state_dispenser.delete(message.peer_id)


# Асинхронная отправка сообщений
async def send_messages():
        data = load_data()
        now = datetime.now()

        for chat_id, messages in list(data.items()):
            new_messages = []
            for msg in messages:
                send_date = format_date(msg["date"])
                if send_date and send_date <= now:
                    try:
                        await bot.api.messages.send(
                            peer_id=int(chat_id),  # Отправка в чат
                            message=msg["text"],
                            random_id=0
                        )
                        logger.info(f"Сообщение отправлено в чат {chat_id}: {msg['text'][:30]}...")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")

                    next_date = calculate_next_date(send_date, msg["repeat"])
                    if next_date:
                        msg["date"] = next_date.strftime("%d.%m.%Y %H:%M")
                    else:
                        continue
                new_messages.append(msg)
            data[chat_id] = new_messages

        save_data(data)

