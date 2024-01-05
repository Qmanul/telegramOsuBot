import asyncio
import datetime
import re
from math import ceil

import emoji
from flag import flag
from itertools import islice
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
            inputs = re.findall(r'\".+?\"|\S+', options.args)

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
            usernames, options = self._option_parser_recent(username_options)
        except TypeError:
            await message.answer('Please check your inputs for errors!')
            return

        username_fin = None

        if not usernames:
            if not db_user:
                await message.answer('No players found.')
                return
            username_fin = db_user['username']

        if not username_fin:
            username_fin = list(set(usernames))[0]

        gamemode = 'osu'
        if option_gamemode:
            gamemode = option_gamemode
        elif db_user:
            gamemode = db_user['gamemode']

        user_info = await self.osuAPI.get_user(username_fin, gamemode)
        if not user_info or 'error' in user_info:
            await message.answer('{} was not found'.format(username_fin))
            return

        include_fails = 0 if options['pass'] else 1

        if options['best']:
            play_list = await self.osuAPI.get_user_best(user_id=user_info['id'], mode=gamemode)
            play_dict = dict(sorted({i: play for i, play in enumerate(play_list)}.items(),
                                    key=lambda x: x[1]['created_at'], reverse=True))

        else:
            play_list = await self.osuAPI.get_user_recent(user_id=user_info['id'], mode=gamemode,
                                                          include_fails=include_fails)
            if not play_list:
                await message.answer('{} has no recent plays for {}'.format(user_info['username'],
                                                                            osu_utils.beautify_mode_text(gamemode)))
                return

            play_dict = {i: play for i, play in enumerate(play_list)}

        if options['search']:
            queries = options['search'].replace('"', '').lower().split()
            temp_play_dict = {}
            for index, play_info in play_dict.items():
                if not all(key in play_info for key in ['beatmap', 'beatmapset']):
                    play_dict.pop(index)
                    continue
                map_title = play_info['beatmapset']['title']
                map_artist = play_info['beatmapset']['artist']
                mapper = play_info['beatmapset']['creator']
                diff = play_info['beatmap']['version']
                title = '{} {} {} {}'.format(map_artist, map_title, mapper, diff).lower()
                if any(query in title for query in queries):
                    temp_play_dict[index] = play_info

            if not temp_play_dict:
                await message.answer('{} has no recent plays for {} with those options.'.format(
                    user_info['username'], osu_utils.beautify_mode_text(gamemode)))
                return
            play_dict = temp_play_dict
        if options['index']:
            index = options['index'] - 1
            if index > len(play_dict) or index <= 0:
                await message.answer('{} has no recent plays for {} with those options.'.format(
                    user_info['username'], osu_utils.beautify_mode_text(gamemode)))
                return
            play_fin = play_dict[index]
        else:
            play_fin = play_dict[0]

        if options['list']:
            page = int(options['page']) - 1 if options['page'] else 0
            await self.recent_answer_list(message, user_info, play_dict, gamemode, page)
            return

        if options['best']:
            answer_type = 'Top {}'.format(str(play_fin['index'] + 1))
            tries_count = None
        else:
            answer_type = 'Recent'
            tries_count = await osu_utils.get_number_of_tries(play_list, play_fin['beatmap']['id'])

        await self.recent_answer(message, user_info, play_fin, gamemode, answer_type, tries_count)

    async def recent_answer(self, message: Message, user_info, play_info, gamemode, answer_type, tries_count):
        answer = ''
        beatmap = await self.osuAPI.get_beatmap(play_info['beatmap']['id'])
        filepath = await self.osuAPI.download_beatmap(beatmap_info=beatmap, api='nerinyan')

        header = '{} {} {} Play for {}:\n'.format(flag(user_info['country_code']), answer_type,
                                                  osu_utils.beautify_mode_text(gamemode), user_info['username'])

        title, text, score_date = await osu_utils.create_play_info(play_info, beatmap, filepath, gamemode)

        footer = ''
        footer_tries = '> Try #{} > '.format(tries_count) if tries_count else ''
        footer += footer_tries
        footer += score_date

        answer += header
        answer += title
        answer += text
        answer += footer

        await message.answer(answer, parse_mode=ParseMode.HTML)

    async def recent_answer_list(self, message: Message, user_info, play_dict, gamemode, page):
        answer = ''
        header = '{} Recent {} Plays for {}:\n'.format(flag(user_info['country_code']),
                                                       osu_utils.beautify_mode_text(gamemode), user_info['username'])
        answer += header
        page = 5 * page
        max_page = ceil(len(play_dict)/5)
        if page > max_page:
            await message.answer('{} has no recent plays for {} with those options.'.format(
                user_info['username'], osu_utils.beautify_mode_text(gamemode)))
            return

        for index, play_info in islice(play_dict.items(), page, page + min(len(play_dict) - page, 5)):
            beatmap = await self.osuAPI.get_beatmap(play_info['beatmap']['id'])
            filepath = await self.osuAPI.download_beatmap(beatmap_info=beatmap, api='nerinyan')
            title, text, score_date = await osu_utils.create_play_info(play_info, beatmap, filepath, gamemode)

            answer += '{}) '.format(index + 1)
            answer += title
            answer += text
            answer += '> Score Set On {}\n'.format(score_date)

        footer = 'On osu! Bancho Server | Page {} of {}'.format(page + 1, max_page)
        answer += footer
        await message.answer(answer, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return

    async def process_user_info(self, message: Message, options: CommandObject, gamemode='osu'):
        user = message.from_user
        inputs = []
        if options.args:
            inputs = re.findall(r'\".+?\"|\S+', options.args)

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
            usernames, options = self._option_parser_user_info(username_options)
        except TypeError:
            await message.answer('Please check your inputs for errors!')
            return

        username_fin = None

        if not usernames:
            if not db_user:
                await message.answer('No players found.')
                return
            username_fin = db_user['username']

        if not username_fin:
            username_fin = list(set(usernames))[0]

        if option_gamemode:
            gamemode = option_gamemode
        elif db_user:
            gamemode = db_user['gamemode']

        user_info = await self.osuAPI.get_user(username_fin, gamemode)

        if options['recent']:
            return

        if options['beatmaps']:
            bmp_type = options['beatmaps']
            return

        if options['mostplayed']:
            return

        if options['detailed']:
            return

        await self.user_info_answer(message, user_info, gamemode)
        return


    async def user_info_answer(self, message: Message, user, gamemode):
        answer = ''
        header_temp = '{} {} Profile for {}\n'.format(flag(user['country_code']),
                                                      osu_utils.beautify_mode_text(gamemode),
                                                      user['username'])
        header = hlink(header_temp, await self.osuAPI.get_user_url(user['id']))

        text = ''
        rank = '#{}'.format(user['statistics']['global_rank']) if user['statistics']['global_rank'] else '-'
        country_rank = '#{}'.format(user['statistics']['country_rank']) if user['statistics']['country_rank'] else ''
        text_rank = '> <b>Bancho Rank:</b> {} ({}{})\n'.format(rank, user['country_code'], country_rank)
        text += text_rank

        peak_rank_date = datetime.datetime.fromisoformat(user['rank_highest']['updated_at'][:-1]).strftime(
            '%d.%m.%Y %H:%M')
        text_peak_rank = '> <b>Peak Rank:</b> #{} achived on {}\n'.format(user['rank_highest']['rank'], peak_rank_date)
        text += text_peak_rank

        text_level = '> <b>Level:</b> {} + {}%\n'.format(user['statistics']['level']['current'],
                                                         user['statistics']['level']['progress'])
        text += text_level

        text_pp_accuracy = '> <b>PP:</b> {:0.2f} <b>Acc:</b> {:0.2f}%\n'.format(user['statistics']['pp'],
                                                                                user['statistics']['hit_accuracy'])
        text += text_pp_accuracy

        text_playcount = '> <b>Playcount:</b> {} ({} hrs)\n'.format(user['statistics']['play_count'],
                                                                    round(user['statistics']['play_time'] / 3600))
        text += text_playcount

        grades = user['statistics']['grade_counts']
        text_grades = '> <b>Ranks:</b> SSH:{} SS:{} SH:{} S:{} A:{}\n'.format(grades['ssh'], grades['ss'], grades['sh'],
                                                                              grades['s'], grades['a'])
        text += text_grades

        footer = ''
        footer += emoji.emojize(':green_circle:') if user['is_online'] else emoji.emojize(':red_circle:')

        if user['last_visit']:
            date = datetime.datetime.fromisoformat(user['last_visit'])
            delta = datetime.datetime.now(tz=datetime.timezone.utc) - date
            footer += ' Last Seen {} Hours Ago'.format(round(delta.seconds / 3600))
        footer += ' On osu! Bancho Server'

        answer += header
        answer += text
        answer += footer
        await message.answer(answer, parse_mode=ParseMode.HTML)

    async def test(self, message: Message, options: CommandObject):
        username = options.args
        user = await self.osuAPI.get_user(username)

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
    def _option_parser_recent(inputs):
        option_parser = OptionParser()
        option_parser.add_option(opt='b', opt_value='best', opt_type=None, default=False)
        option_parser.add_option(opt='ps', opt_value='pass', opt_type=None, default=False)
        option_parser.add_option(opt='i', opt_value='index', opt_type=int, default=None)
        option_parser.add_option(opt='p', opt_value='page', opt_type=int, default=None)
        option_parser.add_option(opt='?', opt_value='search', opt_type=str, default=None)
        option_parser.add_option(opt='l', opt_value='list', opt_type=None, default=False)
        usernames, options = option_parser.parse(inputs)

        return usernames, options

    @staticmethod
    def _option_parser_user_info(inputs):
        option_parser = OptionParser()
        option_parser.add_option(opt='r', opt_value='recent', opt_type=None, default=False)
        option_parser.add_option(opt='b', opt_value='beatmaps', opt_type=str, default=None)
        option_parser.add_option(opt='mp', opt_value='mostplayed', opt_type=None, default=False)
        option_parser.add_option(opt='d', opt_value='detailed', opt_type=None, default=False)
        usernames, options = option_parser.parse(inputs)

        return usernames, options
