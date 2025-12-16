# telethon_client.py — инициализация и авторизация Telethon клиента
from telethon import TelegramClient
from dotenv import load_dotenv
import os
import asyncio

from telethon.errors import SessionPasswordNeededError

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

client = TelegramClient("telethon", API_ID, API_HASH)


async def init_telethon():
    """Инициализация и авторизация Telethon клиента"""
    print("🔄 Инициализация Telethon клиента...")

    # Подключаемся к Telegram
    await client.connect()

    # Проверяем, нужна ли авторизация
    if not await client.is_user_authorized():
        print("🔐 Требуется авторизация. Начинаем процесс входа...")
        try:
            # Запрашиваем номер телефона
            phone = input("📱 Введите номер телефона: ")

            # Отправляем код подтверждения
            sent_code = await client.send_code_request(phone)
            print("📨 Код подтверждения отправлен!")

            # Ждем ввода кода
            code = input("🔢 Введите код из Telegram: ")

            # Пытаемся авторизоваться
            await client.sign_in(phone, code)

            print("✅ Авторизация прошла успешно!")
        except SessionPasswordNeededError:
            print("⚠️ Требуется двухфакторная аутентификация")
            password = input("🔑 Введите 2FA пароль: ")
            await client.sign_in(password=password)
            print("✅ Авторизация с 2FA прошла успешно!")
        except Exception as e:
            print(f"❌ Ошибка при авторизации: {e}")
            raise
    else:
        print("✅ Клиент уже авторизован!")
    print("Telethon-клиент авторизирован")
