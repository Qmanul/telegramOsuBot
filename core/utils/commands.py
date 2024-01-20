from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="recent", description="Get user's most recent play."),
        BotCommand(command="osu", description="Get an user's osu profile."),
        BotCommand(command="taiko", description="Get an user's taiko profile."),
        BotCommand(command="mania", description="Get an user's mania profile."),
        BotCommand(command="ctb", description="Get an user's ctb profile."),
        BotCommand(command="link", description="Set your osu username."),
    ]

    await bot.set_my_commands(commands, BotCommandScopeDefault())
