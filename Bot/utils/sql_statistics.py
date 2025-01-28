import sqlite3
from datetime import datetime

# Подключение к базе данных (или создание новой)
conn = sqlite3.connect('files/bot_statistics.db')
cursor = conn.cursor()


# Инициализация базы данных (если таблицы ещё не созданы)
def initialize_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            date TEXT,
            game TEXT,
            platform TEXT,
            quantity INTEGER,
            revenue REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY,
            date TEXT,
            inquiries INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_time (
            id INTEGER PRIMARY KEY,
            date TEXT,
            user_time REAL
        )
    ''')
    conn.commit()


# Добавление данных о продаже
async def add_sale(game, platform, quantity, revenue):
    date = datetime.now().strftime('%d.%m.%Y')
    cursor.execute('''
        INSERT INTO sales (date, game, platform, quantity, revenue)
        VALUES (?, ?, ?, ?, ?)
    ''', (date, game, platform, quantity, revenue))
    conn.commit()


# Добавление данных о запросах к боту
async def add_inquiry():
    date = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        INSERT INTO inquiries (date, inquiries)
        VALUES (?, ?)
    ''', (date, 1))
    conn.commit()


# Добавление времени работы пользователя с ботом
async def add_user_time(user_time):
    """
        Добавить запись о времени работы с пользователем.
        :param user_time: время работы с пользователем (в минутах).
        """
    date = datetime.now().strftime('%d.%m.%Y')
    cursor.execute('''
            INSERT INTO user_time (date, user_time)
            VALUES (?, ?)
        ''', (date, user_time))
    conn.commit()


# Функция для получения общей прибыли и общего количества продаж
async def get_total_revenue_and_sales(start_date=None, end_date=None):
    query = '''
        SELECT SUM(quantity) AS total_sales, SUM(revenue) AS total_revenue 
        FROM sales
    '''
    params = []
    if start_date and end_date:
        query += " WHERE date BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    cursor.execute(query, tuple(params))
    result = cursor.fetchone()
    return {"total_sales": result[0] or 0, "total_revenue": result[1] or 0}


# Функция для получения топ 5 популярных игр
async def get_top_games(start_date=None, end_date=None, top=5):
    query = '''
        SELECT game, SUM(quantity) AS total_sales 
        FROM sales
    '''
    params = []
    if start_date and end_date:
        query += " WHERE date BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    query += " GROUP BY game ORDER BY total_sales DESC LIMIT ?"
    params.append(top)

    cursor.execute(query, tuple(params))
    return cursor.fetchall()


# Функция для получения сводной статистики за период
async def get_summary_stats(start_date=None, end_date=None):
    sales_stats = await get_total_revenue_and_sales(start_date, end_date)
    top_games = await get_top_games(start_date, end_date)

    summary = {
        "total_sales": sales_stats["total_sales"],
        "total_revenue": sales_stats["total_revenue"],
        "top_games": top_games
    }
    return summary


# Функция для получения статистики по обращениям за период
async def get_inquiries_stats(start_date=None, end_date=None):
    query = '''
        SELECT SUM(inquiries) 
        FROM inquiries
    '''
    params = []
    if start_date and end_date:
        query += " WHERE date BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    cursor.execute(query, tuple(params))
    return cursor.fetchone()[0] or 0


# Функция для получения среднего времени пользователя за период
async def get_avg_user_time(start_date=None, end_date=None):
    """
        Получить среднее время работы с пользователем за указанный период.
        :param start_date: начало периода (включительно).
        :param end_date: конец периода (включительно).
        :return: среднее время работы (в минутах).
        """
    query = '''
            SELECT AVG(user_time) 
            FROM user_time 
        '''
    params = []
    if start_date and end_date:
        query += " WHERE date BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    cursor.execute(query, tuple(params))
    return cursor.fetchone()[0] or 0


# Инициализация базы данных
initialize_db()
