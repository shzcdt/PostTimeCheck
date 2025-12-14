# message_parser.py — оптимизированный парсинг сообщений
from telethon_client import client
from datetime import datetime, timedelta
import asyncio

EMPTY_POST_TEXTS = {"buffet", "", " ", "\n", "\t", "null", "none"}


async def get_monthly_messages(channel_links, year, month):
    """
    Оптимизированная функция для сбора постов за конкретный месяц

    Args:
        channel_links: список ссылок на каналы
        year: год
        month: месяц (1-12)
    """
    all_messages = []

    # Создаем границы месяца
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    print(f"[OPTIMIZED] Собираем посты за период: {start_date} - {end_date}")

    for channel_link in channel_links:
        channel_link = channel_link.strip()
        try:
            print(f"[OPTIMIZED] Получаем канал: {channel_link}")
            channel = await client.get_entity(channel_link)

            collected_in_channel = 0
            skipped_old = 0
            skipped_new = 0

            # ПРОБЛЕМА: мы запрашиваем фиксированное количество сообщений (1000)
            # РЕШЕНИЕ: используем offset_date для начала сбора с нужной даты
            print(f"[OPTIMIZED] Запрашиваем сообщения...")

            # Собираем сообщения БЕЗ лимита, но с фильтрацией по дате
            async for message in client.iter_messages(channel, limit=None):
                # Пропускаем удаленные сообщения
                if hasattr(message, 'deleted') and message.deleted:
                    continue

                # Пропускаем служебные сообщения
                if hasattr(message, 'action') and message.action:
                    continue

                # Проверяем дату сообщения
                message_date = message.date.replace(tzinfo=None)

                # Если сообщение новее конца месяца - пропускаем
                if message_date >= end_date:
                    skipped_new += 1
                    continue

                # Если сообщение старше начала месяца - ПРЕРЫВАЕМ цикл
                if message_date < start_date:
                    skipped_old += 1
                    break  # Все последующие сообщения будут еще старше

                # Получаем количество комментариев
                comments_count = 0
                if hasattr(message, 'replies') and message.replies:
                    comments_count = message.replies.replies

                # Получаем количество реакций
                reactions_count = 0
                if hasattr(message, 'reactions') and message.reactions:
                    reactions_count = sum(reaction.count for reaction in message.reactions.results)

                # Получаем количество пересылок
                forwards_count = 0
                if hasattr(message, 'forwards'):
                    forwards_count = message.forwards or 0

                # Фильтр пустых постов
                text = message.message or ""
                stripped_text = text.strip().lower()

                # Проверяем, является ли текст пустым
                is_empty_text = (stripped_text in EMPTY_POST_TEXTS) and (
                        comments_count == 0 and reactions_count == 0)

                # Также считаем пустым постом, если текст пустой и нет взаимодействий
                is_empty_interaction = (not stripped_text and comments_count == 0 and reactions_count == 0)

                if is_empty_text or is_empty_interaction:
                    continue

                # Сохраняем данные сообщения
                message_data = {
                    "channel": channel_link,
                    "text": text,
                    "date": message_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "views": message.views or 0,
                    "comments_count": comments_count,
                    "reactions_count": reactions_count,
                    "forwards_count": forwards_count,
                    "message_id": message.id,
                    "raw_date": message_date
                }

                all_messages.append(message_data)
                collected_in_channel += 1

                # Выводим прогресс каждые 10 сообщений
                if collected_in_channel % 10 == 0:
                    print(f"[OPTIMIZED] {channel_link}: собрано {collected_in_channel} постов")

            print(f"[OPTIMIZED] Канал {channel_link}:")
            print(f"  • Собрано: {collected_in_channel}")
            print(f"  • Пропущено (новые): {skipped_new}")
            print(f"  • Пропущено (старые): {skipped_old}")

        except Exception as e:
            print(f"[OPTIMIZED] Ошибка при получении канала {channel_link}: {type(e).__name__}: {e}")
            continue

    # Сортируем по дате (новые сначала)
    all_messages.sort(key=lambda x: x['raw_date'], reverse=True)

    print(f"[OPTIMIZED] Всего собрано постов: {len(all_messages)}")
    return all_messages


async def get_last_messages(channel_links, limit=0, days=0):
    """
    Универсальная функция для обратной совместимости
    """
    # Если нужно собрать за определенный период (для старых вызовов)
    if days > 0:
        date_limit = datetime.utcnow() - timedelta(days=days)
    else:
        date_limit = None

    all_messages = []

    for channel_link in channel_links:
        channel_link = channel_link.strip()
        try:
            channel = await client.get_entity(channel_link)

            collected = 0
            request_limit = min(limit * 3, 1000) if limit > 0 else 500

            async for message in client.iter_messages(channel, limit=request_limit):
                # Фильтры как в старой версии
                if hasattr(message, 'deleted') and message.deleted:
                    continue
                if hasattr(message, 'action') and message.action:
                    continue

                # Фильтр по дате
                if date_limit and message.date.replace(tzinfo=None) < date_limit:
                    continue

                # Если достигли лимита
                if limit > 0 and collected >= limit:
                    break

                # Получаем данные
                comments_count = 0
                if hasattr(message, 'replies') and message.replies:
                    comments_count = message.replies.replies

                reactions_count = 0
                if hasattr(message, 'reactions') and message.reactions:
                    reactions_count = sum(reaction.count for reaction in message.reactions.results)

                forwards_count = 0
                if hasattr(message, 'forwards'):
                    forwards_count = message.forwards or 0

                # Фильтр пустых постов
                text = message.message or ""
                stripped_text = text.strip().lower()

                is_empty_text = (stripped_text in EMPTY_POST_TEXTS) and (
                        comments_count == 0 and reactions_count == 0)
                is_empty_interaction = (not stripped_text and comments_count == 0 and reactions_count == 0)

                if is_empty_text or is_empty_interaction:
                    continue

                message_data = {
                    "channel": channel_link,
                    "text": text,
                    "date": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "views": message.views or 0,
                    "comments_count": comments_count,
                    "reactions_count": reactions_count,
                    "forwards_count": forwards_count,
                    "message_id": message.id,
                    "raw_date": message.date
                }

                all_messages.append(message_data)
                collected += 1

        except Exception as e:
            print(f"[ERROR] Ошибка: {e}")
            continue

    return all_messages