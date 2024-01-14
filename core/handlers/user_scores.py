from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram import types

from core.osu.osu import Osu


router = Router()
osu = Osu()


@router.message(Command("recent", "rs", prefix=">"))
async def cmd_recent(message: types.Message, command: CommandObject):
    answer = await osu.process_user_recent(message, command)
    await message.answer(answer['answer'], disable_web_page_preview=answer['disable_web_page_preview'],
                         parse_mode=answer['parse_mode'])


@router.message(Command("test", prefix=">"))
async def cmt_test(message: types.Message, command: CommandObject):
    answer = await osu.test(message, command)
    await message.answer(answer['answer'], disable_web_page_preview=answer['disable_web_page_preview'],
                         parse_mode=answer['parse_mode'])
