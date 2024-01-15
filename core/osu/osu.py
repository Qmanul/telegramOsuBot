import re
from aiogram.filters import CommandObject

from config_reader import config
from core.database.database import UserDatabase
from core.osu.osuAPI import OsuApi, NerinyanAPI
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

    async def test(self, options):
        username = options
        user = await self.osuAPI.get_user(username)
        response = await self.osuAPI.get_user_beatmaps(user['id'], bmp_type='most_played')
        print(response)
        return {'answer': '1'}

    async def process_user_inputs(self, telegram_user, args, parse_options):
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
            usernames, options = await self._option_parser(username_options, parse_options)
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
            db_gamemode = db_user['gamemode']
        except KeyError:
            db_gamemode = None
        gamemode = None
        if option_gamemode:
            gamemode = option_gamemode

        return username_fin, gamemode, options, db_gamemode

    @staticmethod
    async def _gamemode_option_parser(inputs):
        option_parser = OptionParser()
        option_parser.add_option('std', 'osu', opt_type=None, default=False)
        option_parser.add_option('osu', 'osu', opt_type=None, default=False)
        option_parser.add_option('taiko', 'taiko', opt_type=None, default=False)
        option_parser.add_option('ctb', 'fruits', opt_type=None, default=False)
        option_parser.add_option('mania', 'mania', opt_type=None, default=False)
        outputs, gamemodes = option_parser.parse(inputs)

        if any(gamemodes.values()):
            gamemode_fin = filter(lambda gamemode:gamemodes[gamemode], gamemodes).__next__()
        else:
            gamemode_fin = None

        return outputs, gamemode_fin

    @staticmethod
    async def _option_parser(inputs, options):
        option_parser = OptionParser()
        for option in options:
            option_parser.add_option(option['opt'], option['opt_value'], option['opt_type'], option['default'])
        return option_parser.parse(inputs)
