from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram import types

from core.osu.osu import Osu


router = Router()
osu = Osu()


@router.message(Command("link", prefix=">"))
async def cmd_set_user(message: types.Message, command: CommandObject):
    await osu.set_user(message, command)
