import asyncio

import aiofiles
import pyttanko
from aiogram.enums import ParseMode
from aiogram.filters import CommandObject
from aiogram.types import Message
from aiogram.utils.markdown import hlink

from core.utils.option_parser import OptionParser
from core.database.database import UserDatabase
from core.osu.osuAPI import OsuApi, NerinyanAPI
from config_reader import config
from core.osu import osu_utils


class Osu:
    def __init__(self):
        self.osuAPI = OsuApi(
            official_client_id=int(config.client_id.get_secret_value()),
            official_client_secret=config.client_secret.get_secret_value()
        )
        self.nerinyanAPI = NerinyanAPI()
        self.user_db = UserDatabase()
        self.gamemodes = ['osu', 'taiko', 'fruits', 'mania']

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
            await self.user_db.update_user(user.id, user_update)
            await message.answer('{}, your username has been removed.'.format(
                user.first_name))
            return

        osu_user = None

        for gamemode in self.gamemodes:
            osu_user = await self.osuAPI.get_user(username, gamemode)
            if osu_user:
                break
            await asyncio.sleep(.5)

        if not osu_user:
            await message.answer("{} doesn't exists".format(username))
            return

        if not await self.user_db.check_user_exists(user.id):
            await self.user_db.create_new_user(user, osu_user)
            await message.answer('{}, your account has been linked to `{}`.'.format(
                user.first_name, osu_user['username']
            ))
        else:
            user_update = {
                'user_id': osu_user['id'],
                'username': osu_user['username']
            }
            await self.user_db.update_user(user.id, user_update)
            await message.answer('{}, your username has been edited to `{}`'.format(
                user.first_name, osu_user['username']
            ))

    # get user's recent score
    async def process_user_recent(self, message: Message, options: CommandObject):
        user = message.from_user
        inputs = []
        if options.args:
            inputs = options.args.split()

        db_user = await self.user_db.get_user(user.id)
        if db_user:
            db_user = {  # fuck tuples
                'telegram_user_id': db_user[0],
                'username': db_user[1],
                'user_id': db_user[2],
                'gamemode': db_user[3]
            }

        try:
            username_options, option_gamemode = self._gamemode_option_parser(inputs)
            usernames, options = self._option_parser(username_options)
        except TypeError:
            await message.answer('Please check your inputs for errors!')
            return

        final_username = None

        if not usernames:
            if not db_user:
                await message.answer('No players found.')
                return
            final_username = db_user['username']

        if not final_username:
            final_username = list(set(usernames))[0]

        gamemode = 'osu'
        if option_gamemode:
            gamemode = option_gamemode
        elif db_user:
            gamemode = db_user['gamemode']

        user_info = await self.osuAPI.get_user(final_username, gamemode)
        if not user_info:
            await message.answer('{} was not found'.format(final_username))
            return

        play_fin = None
        if options['best']:
            pass

        else:
            user_recent_list = await self.osuAPI.get_user_recent(user_id=user_info['id'], mode=gamemode)
            if not user_recent_list:
                await message.answer('{} has no recent plays for {}'.format(user_info['username'], gamemode))
                return
            play_fin = user_recent_list[0]

        if options['pass']:
            pass

        if options['page']:
            pass

        if options['index']:
            pass

        if options['search']:
            pass

        if options['list']:
            pass

        await self.create_recent_answer(message, user_info, play_fin, gamemode)

    async def create_recent_answer(self, message: Message, user_info, play_info, gamemode):
        answer = ''
        play_statistics = play_info['statistics']
        beatmap = await self.osuAPI.get_beatmap(play_info['beatmap']['id'])

        header = 'Recent {} play for {}:\n'.format(osu_utils.beautify_mode_text(gamemode), user_info['username'])
        answer += header

        mods = ''.join(play_info['mods']) if play_info['mods'] else 'NoMod'
        title = '{}{}+{}[{}]\n'.format(
            beatmap['beatmapset']['title'], beatmap['version'], mods,
            beatmap['difficulty_rating'])
        title_fin = hlink(title, beatmap['url'])
        answer += title_fin

        filepath = await self.nerinyanAPI.download_osu_file(beatmap=beatmap)
        bmap = pyttanko.parser().map(open(filepath))

        play_pp = await osu_utils.calculate_pp(mods=mods, bmp=bmap, info={'play_info': play_info})  #play_info['pp'] if play_info['pp'] is not None else

        text = '> {} > {:0.2f}PP > {:0.2f}%\n> {} > x{}/{} > [{}/{}/{}/{}]'.format(
            play_info['rank'], play_pp, play_info['accuracy'] * 100, play_info['score'], play_info['max_combo'],
            beatmap['max_combo'], play_statistics['count_300'], play_statistics['count_100'],
            play_statistics['count_50'], play_statistics['count_miss']
        )
        answer += text

        await message.answer(answer, parse_mode=ParseMode.HTML)

    @staticmethod
    def _gamemode_option_parser(inputs):
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
    def _option_parser(inputs):
        option_parser = OptionParser()
        option_parser.add_option(opt='b', opt_value='best', opt_type=None, default=False)
        option_parser.add_option(opt='ps', opt_value='pass', opt_type=None, default=None)
        option_parser.add_option(opt='p', opt_value='page', opt_type=int, default=None)
        option_parser.add_option(opt='i', opt_value='index', opt_type=int, default=None)
        option_parser.add_option(opt='?', opt_value='search', opt_type=str, default=None)
        option_parser.add_option(opt='l', opt_value='list', opt_type=None, default=False)
        usernames, options = option_parser.parse(inputs)

        return usernames, options
