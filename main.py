# main.py — запускает Telegram-бота
import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from telegram.ext import ConversationHandler, MessageHandler, filters
from handlers import (
    start, get_channel_link, choose_period, get_post_limit, cancel, help_command,
    ASK_LINK, ASK_PERIOD, ASK_LIMIT, test_channel_command
)
from telethon_client import init_telethon

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def main():
    # Инициализируем Telethon клиент
    await init_telethon()

    # Создаем приложение бота
    app = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_channel_link)],
            ASK_PERIOD: [
                CommandHandler("last_week", choose_period),
                CommandHandler("last_month", choose_period),
                CommandHandler("all", choose_period),
                CommandHandler("custom", choose_period),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_period)
            ],
            ASK_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_post_limit)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("help", help_command)
        ],
    )

    # Добавляем обработчики команд
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("test", test_channel_command))

    print("✅ Бот запущен и готов к работе!")
    print(f"🤖 Имя бота: @{(await app.bot.getMe()).username}")

    # Запускаем бота
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Бот работает до принудительной остановки
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())