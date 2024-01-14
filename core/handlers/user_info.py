from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram import types

from core.osu.osu_info import OsuInfo


osu = OsuInfo()
router = Router()


@router.message(Command("link", prefix=">"))
async def cmd_set_user(message: types.Message, command: CommandObject):
    answer = await osu.process_set_user(message.from_user, command.args)
    await message.answer(answer['answer'], parse_mode=ParseMode.HTML)


@router.message(Command("osu", "std", prefix=">"))
async def cmd_set_user(message: types.Message, command: CommandObject):
    answer = await osu.process_user_info(message.from_user, command.args, gamemode='osu')
    try:
        await message.answer_photo(photo=answer['photo'], caption=answer['answer'], parse_mode=ParseMode.HTML)
    except KeyError:
        await message.answer(answer['answer'], parse_mode=ParseMode.HTML)


@router.message(Command("taiko", prefix=">"))
async def cmd_set_user(message: types.Message, command: CommandObject):
    answer = await osu.process_user_info(message.from_user, command.args, gamemode='taiko')
    try:
        await message.answer_photo(photo=answer['photo'], caption=answer['answer'], parse_mode=ParseMode.HTML)
    except KeyError:
        await message.answer(answer['answer'], parse_mode=ParseMode.HTML)


@router.message(Command("ctb", 'fruits', prefix=">"))
async def cmd_set_user(message: types.Message, command: CommandObject):
    answer = await osu.process_user_info(message.from_user, command.args, gamemode='fruits')
    try:
        await message.answer_photo(photo=answer['photo'], caption=answer['answer'], parse_mode=ParseMode.HTML)
    except KeyError:
        await message.answer(answer['answer'], parse_mode=ParseMode.HTML)


@router.message(Command("mania", "piano", prefix=">"))
async def cmd_set_user(message: types.Message, command: CommandObject):
    answer = await osu.process_user_info(message.from_user, command.args, gamemode='mania')
    try:
        await message.answer_photo(photo=answer['photo'], caption=answer['answer'], parse_mode=ParseMode.HTML)
    except KeyError:
        await message.answer(answer['answer'], parse_mode=ParseMode.HTML)