import sqlite3
from contextlib import closing
from openpyxl.workbook import Workbook

DB_NAME = "postspy.db"


def init_db():
    with closing(sqlite3.connect(DB_NAME)) as conn:
        with conn:
            # Создаем таблицу если её нет
            conn.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT,
                    text TEXT, 
                    date TEXT,
                    views INTEGER, 
                    comments_count INTEGER,
                    reactions_count INTEGER
                )
            ''')

            # Проверяем наличие колонки channel и добавляем если её нет
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(posts)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'channel' not in columns:
                print("[V] Добавляем колонку 'channel' в таблицу posts...")
                conn.execute('ALTER TABLE posts ADD COLUMN channel TEXT')

            if 'comments_count' not in columns:
                print("[V] Добавляем колонку 'comments_count' в таблицу posts...")
                conn.execute('ALTER TABLE posts ADD COLUMN comments_count INTEGER')

        if 'forwards_count' not in columns:
            print("[V] Добавляем колонку 'forwards_count' в таблицу posts...")
            conn.execute('ALTER TABLE posts ADD COLUMN forwards_count INTEGER DEFAULT 0')


def save_post(data: dict):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
            INSERT INTO posts (channel, text, date, views, comments_count, reactions_count, forwards_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
        data.get("channel", ""),
        data.get("text", ""),
        data.get("date", ""),
        data.get("views", 0),
        data.get("comments_count", 0),
        data.get("reactions_count", 0),
        data.get("forwards_count", 0),
    ))

    conn.commit()
    conn.close()


def export_posts_to_excel(filename="exported_posts.xlsx"):
    conn = sqlite3.connect("postspy.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM posts")
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]

    wb = Workbook()
    ws = wb.active
    ws.title = "Posts"

    ws.append(columns)

    for row in rows:
        ws.append(row)

    wb.save(filename)
    conn.close()
    print(f"[V] Данные экспортированы в файл: {filename}")


def clear_posts_table():
    conn = sqlite3.connect("postspy.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts")
    conn.commit()
    conn.close()
    print("[V] Таблица 'posts' очищена.")


# Функция для полной пересоздания таблицы (если нужно)
def recreate_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS posts")
    conn.commit()
    conn.close()
    init_db()
    print("[V] Таблица 'posts' пересоздана с новой структурой.")