import asyncio
from aiogram.filters import CommandObject
from aiogram.types import Message

from core.utils.option_parser import OptionParser
from core.database.database import Database
from core.osu.osuAPI import OsuApi
from config_reader import config


class Osu:
    def __init__(self):
        self.osuAPI = OsuApi(
            official_client_id=int(config.client_id.get_secret_value()),
            official_client_secret=config.client_secret.get_secret_value()
        )
        self.db = Database()

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
            await self.db.update_user(user.id, user_update)
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

        if not await self.db.check_user_exists(user.id):
            await self.db.create_new_user(user, osu_user)
            await message.answer('{}, your account has been linked to `{}`.'.format(
                user.first_name, osu_user['username']
            ))
        else:
            user_update = {
                'user_id': osu_user['id'],
                'username': osu_user['username']
            }
            await self.db.update_user(user.id, user_update)
            await message.answer('{}, your username has been edited to `{}`'.format(
                user.first_name, osu_user['username']
            ))

    async def recent(self, message: Message, command: CommandObject):
        options = command.args
        await self.process_user_recent(message, options)

    async def process_user_recent(self, message: Message, options):
        user = message.from_user

        db_user = await self.db.get_user(user.id)
        db_user = {
            'telegram_user_id': db_user[0],
            'username': db_user[1],
            'user_id': db_user[2],
            'gamemode': db_user[3]
        }

        try:
            outputs, option_gamemode = self._gamemode_option_parser(options)
            option_parser = OptionParser()
            option_parser.add_option('b', 'best', opt_type=None, default=False)
            option_parser.add_option('m', 'gamemode', opt_type='str', default=None)
            option_parser.add_option('ps', 'pass', opt_type=None, default=None)
            option_parser.add_option('p', 'page', opt_type=int, default=None)
            option_parser.add_option('i', 'index', opt_type='range', default=None)
            option_parser.add_option('?', 'search', opt_type='str', default=None)
            option_parser.add_option('np', 'now_playing', opt_type='str', default=False)
            option_parser.add_option('g', 'graph', opt_type=None, default=False)
            option_parser.add_option('l', 'list', opt_type=None, default=False)
            option_parser.add_option('10', 'cond_10', opt_type=None, default=False)
            option_parser.add_option('im', 'image', opt_type=None, default=False)
            option_parser.add_option('u', 'user', opt_type=None, default=False)
            usernames, options = option_parser.parse(outputs)
        except TypeError:
            await message.answer('Please check your inputs for errors!')
            return

        usernames = list(set(usernames))
        if not usernames:
            username = db_user['username']
        else:
            username = usernames[0]

        gamemode = None
        if option_gamemode:
            gamemode = option_gamemode
        if options['gamemode']:
            gamemode = int(option_gamemode)
        if db_user:
            gamemode = int(db_user['gamemode'])
        if gamemode is None:
            gamemode = 0

    def _gamemode_option_parser(self, inputs):
        option_parser = OptionParser()
        option_parser.add_option('std', '0', opt_type=None, default=False)
        option_parser.add_option('osu', '0', opt_type=None, default=False)
        option_parser.add_option('taiko', '1', opt_type=None, default=False)
        option_parser.add_option('ctb', '2', opt_type=None, default=False)
        option_parser.add_option('mania', '3', opt_type=None, default=False)
        outputs, options = option_parser.parse(inputs)

        gamemode = None
        for option in options:
            if options[option]:
                gamemode = int(option)

        return outputs, gamemode
