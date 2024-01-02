from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram import types

from core.osu.osu import Osu


router = Router()
osu = Osu()


@router.message(Command("recent", "rs", prefix=">"))
async def cmd_recent(message: types.Message, command: CommandObject):
    await osu.process_user_recent(message, command)
