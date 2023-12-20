import asyncio
from aiogram.filters import CommandObject
from aiogram.types import Message

from core.database import sqlite
from core.osu.osuAPI import OsuApi
from config_reader import config


class Osu:
    def __init__(self):
        self.osuAPI = OsuApi(
            official_client_id=int(config.client_id.get_secret_value()),
            official_client_secret=config.client_secret.get_secret_value()
        )

    async def set_user(self, message: Message, command: CommandObject):
        if command.args is None:
            await message.answer('No username')
            return
        username = command.args
        await self.process_set_user(username=username, message=message)

    async def process_set_user(self, username, message: Message):
        user = message.from_user

        if username == 'NONE':
            user_update = {
                'username': None,
                'user_id': None
            }
            await sqlite.update_user(user.id, user_update)
            await message.answer('{}, your username has been removed.'.format(
                user.first_name))
            return

        gamemodes = [0, 1, 2, 3]
        osu_user = None

        for gamemode in gamemodes:
            osu_user = await self.osuAPI.get_user(username, gamemode)
            if osu_user:
                break
            await asyncio.sleep(.5)

        if not osu_user:
            await message.answer("{} doesn't exists".format(username))

        if not await sqlite.check_user_exists(user.id):
            await sqlite.create_new_user(user, osu_user)
            await message.answer('{}, your account has been linked to `{}`.'.format(
                user.first_name, osu_user['username']
            ))
        else:
            user_update = {
                'user_id': osu_user['id'],
                'username': osu_user['username']
            }
            await sqlite.update_user(user.id, user_update)
            await message.answer('{}, your username has been edited to `{}`'.format(
                user.first_name, osu_user['username']
            ))

    async def recent(self, message: Message, command: CommandObject):
        options = command.args
        await self.process_user_recent(message, options)

    async def process_user_recent(self, message: Message, options):
        user = message.from_user

        db_user = await sqlite.get_user(user.id)

        if db_user:
            gamemode = int(db_user['gamemode'])
        else:
            gamemode = 0

        # userinfo = self.osuAPI.get_user()

        # try:
            # play_list = self.osuAPI.get_user_recent(user_id=1)

    def _gamemode_option_parser(self, options):

