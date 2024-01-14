from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram import types

from core.osu.osu import Osu

router = Router()
osu = Osu()


@router.message(Command("link", prefix=">"))
async def cmd_set_user(message: types.Message, command: CommandObject):
    answer = await osu.process_set_user(message, command)
    await message.answer(answer['answer'], disable_web_page_preview=answer['disable_web_page_preview'],
                         parse_mode=ParseMode.HTML)


@router.message(Command("osu", "std", prefix=">"))
async def cmd_set_user(message: types.Message, command: CommandObject):
    answer = await osu.process_user_info(message, command, gamemode='osu')
    try:
        await message.answer_photo(photo=answer['photo'], caption=answer['answer'],
                                   disable_web_page_preview=answer['disable_web_page_preview'],
                                   parse_mode=ParseMode.HTML)
    except KeyError:
        await message.answer(answer['answer'], disable_web_page_preview=answer['disable_web_page_preview'],
                             parse_mode=ParseMode.HTML)
