from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram import types

from core.osu.osu_recent import OsuRecent

user_scores_router = Router()
osu = OsuRecent()


@user_scores_router.message(Command("start", prefix="/>"))
async def cmd_recent(message: types.Message, command: CommandObject):

    await message.answer('', parse_mode=ParseMode.HTML)
