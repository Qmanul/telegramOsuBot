from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram import types

from core.osu.osu_recent import OsuRecent

user_scores_router = Router()
osu = OsuRecent()


@user_scores_router.message(Command("recent", "rs", prefix="/>"))
async def cmd_recent(message: types.Message, command: CommandObject):
    answer = await osu.process_user_recent(message.from_user, command.args)
    if 'photo' in answer:
        return await message.answer_photo(photo=answer['photo'], caption=answer['answer'], parse_mode=ParseMode.HTML)

    try:
        await message.answer(answer['answer'], disable_web_page_preview=answer['disable_web_page_preview'],
                             parse_mode=ParseMode.HTML)
    except KeyError:
        await message.answer(answer['answer'], parse_mode=ParseMode.HTML)
