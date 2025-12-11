# import asyncio
# from telethon_client import init_telethon
# from utils.message_parser import get_last_messages
# from utils.database import save_post, init_db
# from utils.database import export_posts_to_excel
# from utils.database import clear_posts_table
#
#
# async def main():
#     await init_telethon()
#     init_db()
#     clear_posts_table()
#     channel = "rinpivkotgc"
#     messages = await get_last_messages(channel, limit=30)
#
#     for msg in messages:
#         save_post(msg)
#         print(msg)
#     print(len(messages))
#     export_posts_to_excel()
#
# if __name__ == "__main__":
#     asyncio.run(main())