# handlers.py — команды бота (/start, /monthly_report)
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime, timedelta
import asyncio

from utils.message_parser import get_last_messages, get_monthly_messages

# Константы для ConversationHandler
ASK_CHANNELS, ASK_MONTH, ASK_YEAR = range(3)


async def generate_monthly_report_for_channels(channels, year, month):
    """
    Generate monthly report for specified channels (1-4 channels)
    """

    print(f"[REPORT] Generating report for {len(channels)} channels: {channels}")
    print(f"[REPORT] Period: {year}-{month:02d}")

    # Используем оптимизированную функцию
    monthly_posts = await get_monthly_messages(channels, year, month)

    # Группируем посты по каналам
    posts_by_channel = {}
    for post in monthly_posts:
        channel = post['channel']
        if channel not in posts_by_channel:
            posts_by_channel[channel] = []
        posts_by_channel[channel].append(post)


    # Словарь для хранения статистики по каналам
    channel_stats = {}

    for channel in channels:
        posts = posts_by_channel.get(channel, [])

        print(f"[REPORT] Channel {channel}: {len(posts)} posts in {month}-{year}")

        if posts:
            # Рассчитываем статистику
            total_posts = len(posts)
            total_views = sum(post.get('views', 0) for post in posts)
            avg_views = round(total_views / total_posts, 2) if total_posts > 0 else 0

            total_reactions = sum(post.get('reactions_count', 0) for post in posts)
            total_comments = sum(post.get('comments_count', 0) for post in posts)
            total_forwards = sum(post.get('forwards_count', 0) for post in posts)

            # Средние значения на пост
            avg_reactions = round(total_reactions / total_posts, 2) if total_posts > 0 else 0
            avg_comments = round(total_comments / total_posts, 2) if total_posts > 0 else 0
            avg_forwards = round(total_forwards / total_posts, 2) if total_posts > 0 else 0

            # Охваты
            coverage_per_reaction = round(total_views / total_reactions, 2) if total_reactions > 0 else 0
            coverage_per_forward = round(total_views / total_forwards, 2) if total_forwards > 0 else 0
            coverage_per_comment = round(total_views / total_comments, 2) if total_comments > 0 else 0

            channel_stats[channel] = {
                'total_posts': total_posts,
                'avg_views': avg_views,
                'total_reactions': total_reactions,
                'avg_reactions': avg_reactions,
                'total_comments': total_comments,
                'avg_comments': avg_comments,
                'total_forwards': total_forwards,
                'avg_forwards': avg_forwards,
                'coverage_per_reaction': coverage_per_reaction,
                'coverage_per_forward': coverage_per_forward,
                'coverage_per_comment': coverage_per_comment
            }
        else:
            # Если постов нет
            channel_stats[channel] = {
                'total_posts': 0,
                'avg_views': 0,
                'total_reactions': 0,
                'avg_reactions': 0,
                'total_comments': 0,
                'avg_comments': 0,
                'total_forwards': 0,
                'avg_forwards': 0,
                'coverage_per_reaction': 0,
                'coverage_per_forward': 0,
                'coverage_per_comment': 0
            }

    return channel_stats


async def monthly_report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога для получения ежемесячного отчета"""
    await update.message.reply_text(
        "📊 *Ежемесячный отчет по Telegram-каналам*\n\n"
        "Я могу сгенерировать подробную статистику по 1-4 каналам "
        "за любой месяц.\n\n"
        "📌 *Что я делаю:*\n"
        "1. Собираю все посты за указанный месяц\n"
        "2. Анализирую просмотры, реакции, комментарии и пересылки\n"
        "3. Рассчитываю средние значения и охваты\n"
        "4. Формирую удобный отчет\n\n"
        "✍️ *Отправьте ссылки на каналы:*\n"
        "Можно указать от 1 до 4 каналов через запятую или с новой строки\n\n"
        "Примеры:\n"
        "@warningbuffet\n"
        "@warningbuffet, @KOTyarovki\n"
        "@warningbuffet, @KOTyarovki, @drawstoks, @CrashSoon\n\n"
        "Или напишите /cancel для отмены",
        parse_mode='Markdown'
    )

    return ASK_CHANNELS


async def get_report_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение списка каналов для отчета"""
    raw_text = update.message.text
    channels = []

    # Парсим каналы из сообщения
    for line in raw_text.split('\n'):
        for channel in line.split(','):
            channel = channel.strip()
            if channel:
                # Проверяем формат ссылки
                if channel.startswith('@') or channel.startswith('https://t.me/'):
                    channels.append(channel)
                elif 't.me/' in channel:
                    # Добавляем https:// если нет
                    if not channel.startswith('http'):
                        channel = f"https://{channel}"
                    channels.append(channel)
                else:
                    # Пробуем добавить @ если это просто имя
                    channels.append(f"@{channel}")

    # Проверяем количество каналов
    if not channels:
        await update.message.reply_text(
            "❌ Не найдено валидных ссылок на каналы.\n\n"
            "Пожалуйста, отправьте ссылки в формате:\n"
            "@channelname или https://t.me/channelname\n\n"
            "Можно от 1 до 4 каналов через запятую."
        )
        return ASK_CHANNELS

    if len(channels) > 4:
        await update.message.reply_text(
            "❌ Слишком много каналов!\n"
            "Максимум можно указать 4 канала.\n"
            "Пожалуйста, укажите от 1 до 4 каналов:"
        )
        return ASK_CHANNELS

    # Сохраняем каналы
    context.user_data["channels"] = channels

    # Спрашиваем месяц
    await update.message.reply_text(
        f"✅ Получено каналов: {len(channels)}\n"
        f"📺 Каналы: {', '.join(channels)}\n\n"
        "📅 *За какой месяц нужен отчет?*\n\n"
        "Введите номер месяца (1-12):\n"
        "1 - Январь\n"
        "2 - Февраль\n"
        "3 - Март\n"
        "... и так далее\n\n"
        "Или напишите /cancel для отмены",
        parse_mode='Markdown'
    )

    return ASK_MONTH


async def get_report_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение месяца для отчета"""
    try:
        month = int(update.message.text)

        if month < 1 or month > 12:
            await update.message.reply_text(
                "❌ Месяц должен быть от 1 до 12.\n"
                "Пожалуйста, введите число от 1 до 12:"
            )
            return ASK_MONTH

        # Сохраняем месяц
        context.user_data["month"] = month

        # Спрашиваем год
        current_year = datetime.now().year
        await update.message.reply_text(
            f"✅ Месяц: {month}\n\n"
            "📅 *За какой год нужен отчет?*\n\n"
            f"Введите год (например, {current_year}):\n"
            f"Минимум: {current_year - 1}\n"
            f"Максимум: {current_year}\n\n"
            "Или напишите /cancel для отмены",
            parse_mode='Markdown'
        )

        return ASK_YEAR

    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число от 1 до 12:"
        )
        return ASK_MONTH


async def get_report_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение года и генерация отчета"""
    try:
        year = int(update.message.text)
        current_year = datetime.now().year

        if year < current_year - 1 or year > current_year:
            await update.message.reply_text(
                f"❌ Год должен быть от {current_year - 1} до {current_year}.\n"
                "Пожалуйста, введите корректный год:"
            )
            return ASK_YEAR

        # Получаем данные из контекста
        channels = context.user_data.get("channels", [])
        month = context.user_data.get("month", 1)

        # Названия месяцев для красивого вывода
        month_names = [
            "", "январь", "февраль", "март", "апрель", "май", "июнь",
            "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
        ]

        month_name = month_names[month]

        # Сообщение о начале сбора
        processing_msg = await update.message.reply_text(
            f"🔄 Собираю статистику за {month_name} {year} года...\n"
            f"Каналы: {', '.join(channels)}\n\n"
            "Это может занять несколько минут..."
        )

        # Генерируем отчет
        channel_stats = await generate_monthly_report_for_channels(channels, year, month)

        # Формируем отчет
        report_text = f"📊 *Отчет за {month_name} {year} года*\n\n"
        report_text += f"*Период:* {month_name.capitalize()} {year}\n"
        report_text += f"*Количество каналов:* {len(channels)}\n"
        report_text += "*" * 40 + "\n\n"

        # Статистика по каждому каналу
        for i, channel in enumerate(channels, 1):
            stats = channel_stats.get(channel, {})

            report_text += f"*{i}. {channel}*\n"
            report_text += f"   📝 Постов: {stats.get('total_posts', 0)}\n"
            report_text += f"   📊 Средний просмотров на пост: {stats.get('avg_views', 0)}\n"
            report_text += f"   ❤️ Реакций: {stats.get('avg_reactions', 0)}\n"
            report_text += f"   💬 Комментариев: {stats.get('avg_comments', 0)}\n"
            report_text += f"   🔄 Пересылок: {stats.get('avg_forwards', 0)}\n\n"

            # Охваты (если есть данные)
            if stats.get('total_reactions', 0) > 0:
                report_text += f"   📈 Охват на реакцию: {stats.get('coverage_per_reaction', 0)}\n"
            if stats.get('total_comments', 0) > 0:
                report_text += f"   📈 Охват на комментарий: {stats.get('coverage_per_comment', 0)}\n"
            if stats.get('total_forwards', 0) > 0:
                report_text += f"   📈 Охват на пересылку: {stats.get('coverage_per_forward', 0)}\n"

            report_text += "\n" + "-" * 30 + "\n\n"

        report_text += "*" * 40 + "\n"
        report_text += "✅ Отчет сгенерирован!\n"
        report_text += "Для нового отчета отправьте /monthly"

        # Отправляем отчет
        await processing_msg.edit_text(report_text, parse_mode='Markdown')

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректный год:"
        )
        return ASK_YEAR
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка при генерации отчета: {str(e)[:100]}"
        )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена диалога"""
    await update.message.reply_text(
        "❌ Диалог отменен.\n\n"
        "Для нового отчета отправьте /monthly\n"
        "Для начала работы отправьте /start"
    )
    context.user_data.clear()
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы с ботом"""
    await update.message.reply_text(
        "🤖 *Добро пожаловать в PostSpy!*\n\n"
        "Я - бот для анализа статистики Telegram-каналов.\n\n"
        "📊 *Что я умею:*\n"
        "✅ Генерировать ежемесячные отчеты по 1-4 каналам\n"
        "✅ Анализировать просмотры, реакции, комментарии\n"
        "✅ Рассчитывать средние значения и охваты\n\n"
        "🛠 *Доступные команды:*\n"
        "/monthly - 📊 Получить ежемесячный отчет\n"
        "/help - 📖 Справка по использованию\n"
        "/cancel - ❌ Отменить текущий диалог\n\n"
        "Чтобы начать анализ, отправьте команду: /monthly ",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по использованию бота"""
    help_text = """
📖 Справка по использованию PostSpy

Основная команда:
/monthly - получить ежемесячный отчет по каналам

Как получить отчет:
1. Отправьте /monthly
2. Введите ссылки на каналы (1-4 канала)
3. Укажите месяц (1-12)
4. Укажите год

Форматы ссылок на каналы:
• @username
• https://t.me/username
• https://t.me/joinchat/...
• username (я сам добавлю @)

Примеры использования:
• Просто отправьте /monthly и следуйте инструкциям
• Можно анализировать от 1 до 4 каналов за раз

Что анализируется:
✅ Количество постов
✅ Просмотры (общие и средние)
✅ Реакции
✅ Комментарии
✅ Пересылки
✅ Охваты на взаимодействия

Другие команды:
/cancel - отменить текущий диалог
/help - показать эту справку
    """

    await update.message.reply_text(help_text)