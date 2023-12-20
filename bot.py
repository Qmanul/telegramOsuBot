import asyncio
import logging
from aiogram import Bot, Dispatcher

from config_reader import config
from core.database.sqlite import db_start
from core.handlers import user_link


async def main():
    logging.basicConfig(level=logging.INFO)
    await db_start()

    dp = Dispatcher()
    bot = Bot(token=config.bot_token.get_secret_value())

    dp.include_routers(user_link.router)  # user_scores.router

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())