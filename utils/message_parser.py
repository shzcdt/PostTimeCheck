# message_parser.py — парсинг сообщений через Telethon
from telethon_client import client
from datetime import datetime, timedelta
import asyncio


async def get_last_messages(channel_links, limit=0, days=0):
    """
    Собирает посты из каналов

    Args:
        channel_links: список ссылок на каналы
        limit: сколько постов собрать (0 = все)
        days: за сколько дней (0 = все время)
    """
    all_messages = []

    if isinstance(channel_links, str):
        channel_links = [channel_link.strip() for channel_link in channel_links.split(',')]

    # Рассчитываем дату начала периода с учетом часового пояса
    if days > 0:
        # Берем текущее время в UTC (как у Telegram)
        date_limit = datetime.utcnow() - timedelta(days=days)
        print(f"[DEBUG] Дата ограничения: {date_limit}")
        print(f"[DEBUG] Собираем посты НОВЕЕ чем: {date_limit}")
    else:
        date_limit = None

    for channel_link in channel_links:
        channel_link = channel_link.strip()
        try:
            print(f"[DEBUG] Пытаемся получить канал: {channel_link}")
            channel = await client.get_entity(channel_link)
            print(f"[DEBUG] Канал получен: {channel.title if hasattr(channel, 'title') else channel_link}")

            collected_in_channel = 0
            skipped_old = 0
            skipped_other = 0

            # Определяем лимит для запроса
            if limit == 0:
                # Для сбора всех постов за период берем больше
                request_limit = 5000
            else:
                # Берем с запасом для фильтрации
                request_limit = limit * 5 if days > 0 else limit * 2

            print(f"[DEBUG] Запрашиваем {request_limit} сообщений для фильтрации")

            async for message in client.iter_messages(channel, limit=request_limit):
                # Пропускаем удаленные сообщения
                if hasattr(message, 'deleted') and message.deleted:
                    skipped_other += 1
                    continue

                # Пропускаем служебные сообщения
                if hasattr(message, 'action') and message.action:
                    skipped_other += 1
                    continue

                # ФИЛЬТР ПО ДАТЕ: если указан период
                if date_limit:
                    # Сообщение слишком старое - прерываем цикл для этого канала
                    if message.date.replace(tzinfo=None) < date_limit:
                        skipped_old += 1
                        # Не прерываем сразу, а продолжаем искать более новые
                        continue  # <-- ИЗМЕНЕНИЕ: continue вместо break

                # Если есть лимит И мы уже собрали достаточно
                if limit > 0 and collected_in_channel >= limit:
                    break

                # Собираем данные о посте
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
                    "message_id": message.id,
                    "raw_date": message.date  # Сохраняем для отладки
                }
                all_messages.append(message_data)
                collected_in_channel += 1

                # Выводим информацию о каждом собранном посте для отладки
                if collected_in_channel <= 5:  # Первые 5 постов
                    print(f"[DEBUG] Собран пост #{collected_in_channel}: {message.date} - {message.text[:50]}...")

            print(f"[DEBUG] Итог по каналу {channel_link}:")
            print(f"  • Собрано: {collected_in_channel}")
            print(f"  • Пропущено (старые): {skipped_old}")
            print(f"  • Пропущено (другие): {skipped_other}")

            # Небольшая задержка между каналами
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[ERROR] Ошибка при получении канала {channel_link}: {type(e).__name__}: {e}")
            # Пробуем получить канал по другому
            try:
                # Иногда помогает убрать @ или https://
                if channel_link.startswith('@'):
                    clean_link = channel_link[1:]
                    print(f"[DEBUG] Пробуем clean link: {clean_link}")
                    channel = await client.get_entity(clean_link)
                elif 't.me/' in channel_link:
                    clean_link = channel_link.split('t.me/')[-1].replace('/', '')
                    print(f"[DEBUG] Пробуем clean link: {clean_link}")
                    channel = await client.get_entity(clean_link)
            except Exception as e2:
                print(f"[ERROR] Вторая попытка тоже неудачна: {e2}")
                continue

    # Сортируем по дате (новые сначала)
    all_messages.sort(key=lambda x: x['raw_date'], reverse=True)

    # Если есть лимит - берем только указанное количество
    if limit > 0 and len(all_messages) > limit:
        all_messages = all_messages[:limit]

    # Выводим информацию о датах
    if all_messages:
        oldest = min(msg['raw_date'] for msg in all_messages)
        newest = max(msg['raw_date'] for msg in all_messages)
        print(f"[DEBUG] Диапазон дат в результатах:")
        print(f"  • Самый новый: {newest}")
        print(f"  • Самый старый: {oldest}")
        print(f"  • Всего дней: {(newest - oldest).days if newest > oldest else 0}")

    print(f"[DEBUG] Всего собрано постов: {len(all_messages)}")
    return all_messages


async def test_channel(channel_link):
    """Тестовая функция для проверки канала"""
    try:
        channel = await client.get_entity(channel_link)
        print(f"\n[TEST] Проверка канала: {channel_link}")
        print(f"[TEST] Название: {channel.title if hasattr(channel, 'title') else 'N/A'}")

        # Пробуем получить последние 5 сообщений без фильтров
        messages = []
        async for message in client.iter_messages(channel, limit=5):
            messages.append({
                "date": message.date,
                "text": message.text[:100] if message.text else "Нет текста",
                "views": message.views
            })

        print(f"[TEST] Последние сообщения:")
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. {msg['date']} - {msg['text']}... (просмотры: {msg['views']})")

        return True
    except Exception as e:
        print(f"[TEST] Ошибка: {e}")
        return False


async def get_messages_last_month(channel_links, limit=0):
    """Специальная функция для сбора постов за последний месяц"""
    all_messages = []

    if isinstance(channel_links, str):
        channel_links = [channel_link.strip() for channel_link in channel_links.split(',')]

    # Месяц назад от текущей даты
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    print(f"[MONTH] Собираем посты начиная с: {one_month_ago}")

    for channel_link in channel_links:
        try:
            print(f"[MONTH] Обрабатываем канал: {channel_link}")
            channel = await client.get_entity(channel_link)

            collected = 0
            # Берем больше сообщений чтобы найти достаточно за месяц
            async for message in client.iter_messages(channel, limit=1000):
                # Проверяем дату сообщения
                if message.date.replace(tzinfo=None) < one_month_ago:
                    # Сообщение старше месяца, но продолжаем искать
                    continue

                # Пропускаем удаленные и служебные
                if hasattr(message, 'deleted') and message.deleted:
                    continue
                if hasattr(message, 'action') and message.action:
                    continue

                # Собираем данные
                comments_count = message.replies.replies if hasattr(message, 'replies') and message.replies else 0
                reactions_count = sum(r.count for r in message.reactions.results) if hasattr(message,
                                                                                             'reactions') and message.reactions else 0

                message_data = {
                    "channel": channel_link,
                    "text": message.message or "",
                    "date": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "views": message.views or 0,
                    "comments_count": comments_count,
                    "reactions_count": reactions_count
                }
                all_messages.append(message_data)
                collected += 1

                # Если достигли лимита - выходим
                if limit > 0 and collected >= limit:
                    break

            print(f"[MONTH] Канал {channel_link}: собрано {collected} постов за месяц")

        except Exception as e:
            print(f"[MONTH] Ошибка: {e}")
            continue

    print(f"[MONTH] Итого: {len(all_messages)} постов")
    return all_messages