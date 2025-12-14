# main.py — запускает Telegram-бота с функцией ежемесячных отчетов
import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from dotenv import load_dotenv

from handlers import (
    start, help_command, cancel,
    monthly_report_start, get_report_channels, get_report_month, get_report_year,
    ASK_CHANNELS, ASK_MONTH, ASK_YEAR
)
from telethon_client import init_telethon

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def main():
    # Инициализируем Telethon клиент
    await init_telethon()

    # Создаем приложение бота
    app = Application.builder().token(BOT_TOKEN).build()

    # Обработчик для ежемесячного отчета
    monthly_report_handler = ConversationHandler(
        entry_points=[CommandHandler("monthly", monthly_report_start)],
        states={
            ASK_CHANNELS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_report_channels)],
            ASK_MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_report_month)],
            ASK_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_report_year)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("help", help_command)
        ],
    )

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(monthly_report_handler)
    app.add_handler(CommandHandler("cancel", cancel))

    print("✅ Бот запущен и готов к работе!")
    print("🤖 Основная функция: генерация ежемесячных отчетов по 1-4 каналам")

    # Получаем информацию о боте
    bot_info = await app.bot.getMe()
    print(f"🤖 Имя бота: @{bot_info.username}")

    # Запускаем бота
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Бот работает до принудительной остановки
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())