import re

from aiogram.filters import CommandObject
from aiogram.types import BufferedInputFile

from config_reader import config
from core.database.database import UserDatabase
from core.osu.osuAPI import OsuApi, NerinyanAPI
from core.utils import drawing
from core.utils.option_parser import OptionParser


class Osu:
    def __init__(self):
        self.osuAPI = OsuApi(
            official_client_id=int(config.client_id.get_secret_value()),
            official_client_secret=config.client_secret.get_secret_value()
        )
        self.nerinyanAPI = NerinyanAPI()
        self.user_db = UserDatabase()
        self.gamemodes = ['osu', 'taiko', 'fruits', 'mania']
        self.options = {'user_info': [{'opt': 'r', 'opt_value': 'recent', 'opt_type': None, 'default': False},
                                      {'opt': 'b', 'opt_value': 'beatmaps', 'opt_type': str, 'default': None},
                                      {'opt': 'mp', 'opt_value': 'mostplayed', 'opt_type': None, 'default': False},
                                      {'opt': 'd', 'opt_value': 'detailed', 'opt_type': None, 'default': False}],
                        'user_recent': [{'opt': 'b', 'opt_value': 'best', 'opt_type': None, 'default': False},
                                        {'opt': 'ps', 'opt_value': 'pass', 'opt_type': None, 'default': False},
                                        {'opt': 'i', 'opt_value': 'index', 'opt_type': int, 'default': None},
                                        {'opt': 'p', 'opt_value': 'page', 'opt_type': int, 'default': None},
                                        {'opt': '?', 'opt_value': 'search', 'opt_type': str, 'default': None},
                                        {'opt': 'l', 'opt_value': 'list', 'opt_type': None, 'default': False}]
                        }

    async def test(self, options: CommandObject):
        import io
        username = options.args
        user = await self.osuAPI.get_user(username)
        plot = await drawing.plot_profile(user)
        img_byte_arr = io.BytesIO()
        plot.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return {'photo': BufferedInputFile(img_byte_arr, filename='plot.png'), 'answer': ''}

    async def process_user_inputs(self, telegram_user, args, options_type):
        try:
            inputs = re.findall(r'\".+?\"|\S+', args)
        except TypeError:
            inputs = []

        db_user = await self.user_db.get_user(telegram_user.id)
        try:
            db_user = {  # fuck tuples
                'telegram_user_id': db_user[0],
                'username': db_user[1],
                'user_id': db_user[2],
                'gamemode': db_user[3]
            }
        except KeyError:
            pass

        try:
            username_options, option_gamemode = await self._gamemode_option_parser(inputs)
            usernames, options = await self._option_parser(username_options, self.options[options_type])
        except TypeError:
            return 'Please check your inputs for errors!'

        if not usernames:
            try:
                username_fin = db_user['username']
            except KeyError:
                return 'No players found'
        else:
            username_fin = list(set(usernames))[0].replace('"', '')

        try:
            gamemode = db_user['gamemode']
        except KeyError:
            gamemode = None
        if option_gamemode:
            gamemode = option_gamemode

        return username_fin, gamemode, options

    @staticmethod
    async def _gamemode_option_parser(inputs):
        option_parser = OptionParser()
        option_parser.add_option('std', 'osu', opt_type=None, default=False)
        option_parser.add_option('osu', 'osu', opt_type=None, default=False)
        option_parser.add_option('taiko', 'taiko', opt_type=None, default=False)
        option_parser.add_option('ctb', 'fruits', opt_type=None, default=False)
        option_parser.add_option('mania', 'mania', opt_type=None, default=False)
        outputs, gamemodes = option_parser.parse(inputs)

        final_gamemode = None
        for gamemode in gamemodes:
            if gamemodes[gamemode]:
                final_gamemode = str(gamemode)

        return outputs, final_gamemode

    @staticmethod
    async def _option_parser(inputs, options):
        option_parser = OptionParser()
        for option in options:
            option_parser.add_option(option['opt'], option['opt_value'], option['opt_type'], option['default'])
        return option_parser.parse(inputs)
