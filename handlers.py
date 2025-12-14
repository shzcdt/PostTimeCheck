# handlers.py — команды бота (/start, /get_messages и т.д.)
from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes
from datetime import datetime, timedelta

from utils.database import save_post, export_posts_to_excel, init_db, clear_posts_table
from utils.message_parser import get_last_messages, get_messages_last_month

ASK_LINK, ASK_PERIOD, ASK_LIMIT = range(3)
user_data = {}

async def generate_monthly_report_for_channels(channels, year, month):
    """
    Generate monthly report for specified channels
    """
    from collections import defaultdict

    # Dictionary to store aggregated data for each channel
    channel_stats = {}

    for channel in channels:
        # Get posts for the specific month and year
        # We'll collect all posts from the beginning to the end of the month
        start_date = datetime(year, month, 1)

        # Determine end date (first day of next month)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Collect posts for this channel within the date range
        posts = await get_posts_by_date_range([channel], start_date, end_date)

        if posts:
            # Calculate statistics for this channel
            total_posts = len(posts)
            total_views = sum(post.get('views', 0) for post in posts)
            avg_views = round(total_views / total_posts, 2) if total_posts > 0 else 0
            total_reactions = sum(post.get('reactions_count', 0) for post in posts)
            total_comments = sum(post.get('comments_count', 0) for post in posts)
            total_forwards = sum(post.get('forwards_count', 0) for post in posts)

            # Calculate coverage ratios
            coverage_per_reaction = round(total_views / total_reactions, 2) if total_reactions > 0 else 0
            coverage_per_forward = round(total_views / total_forwards, 2) if total_forwards > 0 else 0
            coverage_per_comment = round(total_views / total_comments, 2) if total_comments > 0 else 0

            channel_stats[channel] = {
                'total_posts': total_posts,
                'avg_views': avg_views,
                'total_reactions': total_reactions / total_posts,
                'total_forwards': total_forwards / total_posts,
                'total_comments': total_comments / total_posts,
                'coverage_per_reaction': coverage_per_reaction,
                'coverage_per_forward': coverage_per_forward,
                'coverage_per_comment': coverage_per_comment
            }
        else:
            # If no posts found, set all values to 0
            channel_stats[channel] = {
                'total_posts': 0,
                'avg_views': 0,
                'total_reactions': 0,
                'total_forwards': 0,
                'total_comments': 0,
                'coverage_per_reaction': 0,
                'coverage_per_forward': 0,
                'coverage_per_comment': 0
            }

    return channel_stats


async def get_posts_by_date_range(channel_links, start_date, end_date):
    """
    Get posts from channels within a specific date range
    """
    all_messages = []

    if isinstance(channel_links, str):
        channel_links = [channel_link.strip() for channel_link in channel_links.split(',')]

    from telethon_client import client
    from telethon.tl.types import Channel

    for channel_link in channel_links:
        channel_link = channel_link.strip()
        try:
            print(f"[DATE_RANGE] Getting channel: {channel_link}")
            channel = await client.get_entity(channel_link)

            collected_in_channel = 0

            # Iterate through messages within the date range
            async for message in client.iter_messages(channel, limit=5000):
                # Check if message date is within our range
                if start_date <= message.date.replace(tzinfo=None) < end_date:
                    # Process the message similar to get_last_messages function
                    comments_count = 0
                    if hasattr(message, 'replies') and message.replies:
                        comments_count = message.replies.replies

                    reactions_count = 0
                    if hasattr(message, 'reactions') and message.reactions:
                        reactions_count = sum(reaction.count for reaction in message.reactions.results)

                    message_data = {
                        "channel": channel_link,
                        "text": message.message or "",
                        "date": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                        "views": message.views or 0,
                        "comments_count": comments_count,
                        "reactions_count": reactions_count,
                        "forwards_count": message.forwards or 0,
                        "message_id": message.id
                    }
                    all_messages.append(message_data)
                    collected_in_channel += 1

                # Break if we've gone beyond the date range (messages are ordered from newest to oldest)
                elif message.date.replace(tzinfo=None) < start_date:
                    # Since messages come from newest to oldest, we can stop when we go beyond the start date
                    break

            print(f"[DATE_RANGE] Collected {collected_in_channel} messages from {channel_link}")

        except Exception as e:
            print(f"[DATE_RANGE] Error getting channel {channel_link}: {e}")
            continue

    return all_messages


async def monthly_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command to generate monthly report for 4 channels
    """
    # Check if the user has specified channels in their message
    if not context.args or len(context.args) < 5:  # command + 4 channels
        await update.message.reply_text(
            "📊 Команда для генерации ежемесячного отчета по 4 каналам:\n\n"
            "/monthly_report год месяц @channel1 @channel2 @channel3 @channel4\n\n"
            "Пример: /monthly_report 2025 1 @channel1 @channel2 @channel3 @channel4\n"
            "(для отчета за январь 2025 года)"
        )
        return

    try:
        # Parse arguments: year, month, and 4 channels
        args = context.args
        year = int(args[0])
        month = int(args[1])
        channels = args[2:6]  # 4 channels

        if len(channels) != 4:
            await update.message.reply_text("❌ Необходимо указать ровно 4 канала")
            return

        # Validate month
        if month < 1 or month > 12:
            await update.message.reply_text("❌ Месяц должен быть от 1 до 12")
            return

        # Month names for display
        month_names = [
            "", "январь", "февраль", "март", "апрель", "май", "июнь",
            "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
        ]

        if year < datetime.now().year:
            await update.message.reply_text("❌ К сожалению, бот не может орбрабатывать посты, которые были год и более назад")
            return


        # Notify user about starting collection
        processing_msg = await update.message.reply_text(
            f"🔄 Собираю статистику за {month_names[month]} {year} года по 4 каналам..."
        )

        # Generate the report
        channel_stats = await generate_monthly_report_for_channels(channels, year, month)

        # Format and send the report
        report_text = f"📊 *Статистика за {month_names[month]} {year} года*\n\n"

        for channel in channels:
            stats = channel_stats.get(channel, {
                'total_posts': 0,
                'avg_views': 0,
                'total_reactions': 0,
                'total_forwards': 0,
                'total_comments': 0,
                'coverage_per_reaction': 0,
                'coverage_per_forward': 0,
                'coverage_per_comment': 0
            })

            report_text += f"*{channel}*\n"
            report_text += f"Количество постов: {stats['total_posts']}\n"
            report_text += f"Среднее количество просмотров на пост: {stats['avg_views']}\n"
            report_text += f"Реакции: {stats['total_reactions']}\n"
            report_text += f"Пересылки: {stats['total_forwards']}\n"
            report_text += f"Комментарии: {stats['total_comments']}\n"
            report_text += f"Охваты на реакции: {stats['coverage_per_reaction']}\n"
            report_text += f"Охваты на пересылки: {stats['coverage_per_forward']}\n"
            report_text += f"Охваты на комментарии: {stats['coverage_per_comment']}\n\n"

        await processing_msg.edit_text(report_text, parse_mode='Markdown')

    except ValueError:
        await update.message.reply_text("❌ Год и месяц должны быть числовыми значениями")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при генерации отчета: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога с ботом"""
    await update.message.reply_text(
        "Привет! Я PostSpy - бот для анализа Telegram-каналов за месяц!\n\n"
        "Отправь ссылки на Telegram-каналы для анализа.\n"
        "Можно отправить 4 телеграмм канала для анализа.\n\n"
        "Примеры:\n"
        "@warningbuffet\n"
        "@KOTyarovki, @drawstoks\n"
        "https://t.me/warningbuffet, @CrashSoon\n\n"
        "Главное, чтобы телеграмм каналы были публичные!"
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
