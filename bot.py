import asyncio
import logging
from aiogram import Bot, Dispatcher

from config_reader import config
from core.database.database import UserDatabase
from core.handlers import user_info_handler, user_scores_handler
from core.test import pagination_test


async def main():
    logging.basicConfig(level=logging.INFO)

    await UserDatabase().db_start()

    dp = Dispatcher()
    bot = Bot(token=config.bot_token.get_secret_value())

    dp.include_routers(user_info_handler.router, user_scores_handler.router, pagination_test.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
