import json
from datetime import datetime, timedelta

DB_FILE = "files/messages.json"

# Загрузка данных из файла
def load_data():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Сохранение данных в файл
def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Форматирование даты
def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%d.%m.%Y %H:%M")
    except ValueError:
        return None

# Расчёт следующей даты отправки в зависимости от повторения
def calculate_next_date(send_date, repeat):
    if repeat == "ежедневно":
        return send_date + timedelta(days=1)
    elif repeat == "ежемесячно":
        return send_date + timedelta(days=30)
    elif repeat == "ежегодно":
        return send_date + timedelta(days=365)
    return None