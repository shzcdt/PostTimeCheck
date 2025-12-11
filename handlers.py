# handlers.py — команды бота (/start, /get_messages и т.д.)
from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes
from datetime import datetime, timedelta

from utils.database import save_post, export_posts_to_excel, init_db, clear_posts_table
from utils.message_parser import get_last_messages, get_messages_last_month

ASK_LINK, ASK_PERIOD, ASK_LIMIT = range(3)
user_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога с ботом"""
    await update.message.reply_text(
        "Привет! Я PostSpy - бот для анализа Telegram-каналов!\n\n"
        "Отправь ссылки на Telegram-каналы для анализа.\n"
        "Можно отправить несколько каналов через запятую или с новой строки.\n\n"
        "Примеры:\n"
        "@channel3\n"
        "@channel3, @channel2\n"
        "https://t.me/channel3, @channel2"
    )
    init_db()
    context.user_data.clear()  # Очищаем данные предыдущего диалога
    return ASK_LINK


async def get_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение ссылок на каналы"""
    raw_text = update.message.text
    channels = []

    for line in raw_text.split('\n'):
        for channel in line.split(','):
            channel = channel.strip()
            if channel and (channel.startswith('@') or channel.startswith('https://t.me/')):
                channels.append(channel)

    if not channels:
        await update.message.reply_text(
            "❌ Не найдено валидных ссылок на каналы.\n\n"
            "Пожалуйста, отправьте ссылки в формате:\n"
            "@channelname или https://t.me/channelname\n\n"
            "Можно несколько через запятую или с новой строки.\n"
            "Пример: @telegram, https://t.me/durov"
        )
        return ASK_LINK

    context.user_data["channels"] = channels

    # Добавляем выбор периода
    await update.message.reply_text(
        f"✅ Найдено каналов: {len(channels)}\n"
        f"📺 Каналы: {', '.join(channels[:5])}"
        + (f"\n... и ещё {len(channels) - 5} каналов" if len(channels) > 5 else "") + "\n\n"
                                                                                      "📅 Выберите период для сбора постов:\n\n"
                                                                                      "1️⃣ /last_week - посты за последнюю неделю\n"
                                                                                      "2️⃣ /last_month - посты за последний месяц\n"
                                                                                      "3️⃣ /all - все доступные посты (до 1000)\n"
                                                                                      "4️⃣ /custom - указать количество дней\n\n"
                                                                                      "Или напишите /cancel для отмены"
    )
    return ASK_PERIOD


async def choose_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора периода"""
    period_command = update.message.text

    if period_command == "/last_week":
        days = 7
    elif period_command == "/last_month":
        days = 30
    elif period_command == "/all":
        days = 0  # 0 = все посты
    elif period_command == "/custom":
        await update.message.reply_text(
            "🔢 Введите количество дней для сбора постов (например: 14, 60, 90):\n"
            "Максимум: 365 дней"
        )
        return ASK_PERIOD

    try:
        if period_command == "/custom":
            days = int(update.message.text)
        else:
            context.user_data["days"] = days

        if days > 365:
            await update.message.reply_text("❌ Период не может превышать 365 дней. Введите меньшее число:")
            return ASK_PERIOD

        if days < 0:
            await update.message.reply_text("❌ Период не может быть отрицательным. Введите положительное число:")
            return ASK_PERIOD

        context.user_data["days"] = days

        # Формируем текст о периоде
        if days == 0:
            period_text = "все доступные посты"
        elif days == 7:
            period_text = "последнюю неделю"
        elif days == 30:
            period_text = "последний месяц"
        else:
            period_text = f"последние {days} дней"

        await update.message.reply_text(
            f"📅 Период: {period_text}\n\n"
            "🔢 Сколько последних постов нужно собрать с каждого канала? 📊\n\n"
            "Введите число (например: 50):\n"
            "• 0 = все посты за указанный период\n"
            "• Максимум: 1000 постов"
        )
        return ASK_LIMIT

    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число:")
        return ASK_PERIOD


async def get_post_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение лимита постов и запуск сбора"""
    try:
        limit = int(update.message.text)

        if limit < 0 or limit > 1000:
            await update.message.reply_text("❌ Лимит должен быть от 0 до 1000:")
            return ASK_LIMIT

        context.user_data["limit"] = limit
        channels = context.user_data["channels"]
        days = context.user_data.get("days", 0)

        # Отправляем сообщение
        processing_msg = await update.message.reply_text("🔄 Начинаю сбор данных...")

        # Очищаем таблицу
        clear_posts_table()

        # ВЫБОР ФУНКЦИИ В ЗАВИСИМОСТИ ОТ ПЕРИОДА
        try:
            if days == 30:  # Особый случай - месяц
                print(f"[HANDLER] Используем специальную функцию для месяца")
                messages = await get_messages_last_month(channels, limit)
            else:
                print(f"[HANDLER] Используем обычную функцию (days={days}, limit={limit})")
                messages = await get_last_messages(channels, limit, days)

            if not messages:
                await processing_msg.edit_text(
                    "❌ Не удалось собрать посты.\n\n"
                    "Проверьте:\n"
                    "1. Каналы публичные и доступны\n"
                    "2. В каналах есть посты\n"
                    "3. Попробуйте выбрать /all для всех постов"
                )
                return ConversationHandler.END

            # Сохраняем и экспортируем
            for msg in messages:
                save_post(msg)

            excel_filename = f"posts_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            export_posts_to_excel(excel_filename)

            # Статистика
            stats = (
                f"✅ Готово! Собрано: {len(messages)} постов\n"
                f"📁 Файл: {excel_filename}"
            )

            await processing_msg.edit_text(stats)

            with open(excel_filename, "rb") as file:
                await update.message.reply_document(
                    document=file,
                    filename=excel_filename,
                    caption=f"📊 Результат анализа"
                )

        except Exception as e:
            await processing_msg.edit_text(f"❌ Ошибка: {str(e)[:100]}")
            return ConversationHandler.END

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ Введите число:")
        return ASK_LIMIT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    await update.message.reply_text(
        "❌ Диалог отменен.\n\n"
        "Для начала нового анализа отправьте /start"
    )
    context.user_data.clear()  # Очищаем данные пользователя
    return ConversationHandler.END


# Дополнительные команды для удобства
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку"""
    help_text = """
🤖 *PostSpy - Бот для анализа Telegram-каналов*

*Команды:*
/start - Начать анализ каналов
/help - Показать эту справку
/cancel - Отменить текущий диалог

*Как использовать:*
1. Отправьте /start
2. Введите ссылки на каналы (можно несколько)
3. Выберите период сбора
4. Укажите лимит постов

*Поддерживаемые форматы ссылок:*
• @username
• https://t.me/username
• https://t.me/joinchat/...

*Примеры:*
@telegram
https://t.me/durov
@channel1, @channel2, https://t.me/channel3
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def test_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для тестирования канала"""
    if not context.args:
        await update.message.reply_text("Укажите канал: /test @channelname")
        return

    channel_link = context.args[0]
    await update.message.reply_text(f"🔍 Тестирую канал {channel_link}...")

    from utils.message_parser import test_channel
    success = await test_channel(channel_link)

    if success:
        await update.message.reply_text("✅ Канал доступен")
    else:
        await update.message.reply_text("❌ Канал недоступен")
