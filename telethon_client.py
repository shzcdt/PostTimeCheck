# telethon_client.py — инициализация и авторизация Telethon клиента
from telethon import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

client = TelegramClient("telethon", API_ID, API_HASH)


async def init_telethon():
    await client.start()
    print("Telethon-клиент авторизирован")
