import asyncio
import datetime
import re

import emoji
import oppadc
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
        if not user_info or 'error' in user_info:
            await message.answer('{} was not found'.format(final_username))
            return

        include_fails = 0 if options['pass'] else 1

        play_list = []
        if options['best']:
            play_list = await self.osuAPI.get_user_best(user_id=user_info['id'], mode=gamemode)
            for index, play_info in enumerate(play_list):
                play_info['index'] = index
            play_list.sort(key=lambda x: x['created_at'], reverse=True)

        else:
            play_list = await self.osuAPI.get_user_recent(user_id=user_info['id'], mode=gamemode,
                                                          include_fails=include_fails)
            if not play_list:
                await message.answer('{} has no recent plays for {}'.format(user_info['username'],
                                                                            osu_utils.beautify_mode_text(gamemode)))
                return

        if options['search']:
            queries = options['search'].replace('"', '').lower().split()
            temp_play_list = []
            for play_info in play_list:
                if not all(key in play_info for key in ['beatmap', 'beatmapset']):
                    play_list.remove(play_info)
                    continue
                map_title = play_info['beatmapset']['title']
                map_artist = play_info['beatmapset']['artist']
                mapper = play_info['beatmapset']['creator']
                diff = play_info['beatmap']['version']
                title = '{} {} {} {}'.format(map_artist, map_title, mapper, diff).lower()
                if any(query in title for query in queries):
                    temp_play_list.append(play_info)

            if not temp_play_list:
                await message.answer('{} has no recent plays for {} with those options.'.format(
                    user_info['username'], osu_utils.beautify_mode_text(gamemode)))
                return
            play_list = temp_play_list

        if options['index']:
            index = options['index']
            if index > len(play_list) or index < 1:
                await message.answer('{} has no recent plays for {} with those options.'.format(
                    user_info['username'], osu_utils.beautify_mode_text(gamemode)))
                return
            play_fin = play_list[index-1]
        else:
            play_fin = play_list[0]

        if options['best']:
            answer_type = 'Top {}'.format(str(play_fin['index'] + 1))
            tries_count = None
        else:
            answer_type = 'Recent'
            tries_count = await osu_utils.get_number_of_tries(play_list, play_fin['beatmap']['id'])

        if options['list']:
            pass

        await self.create_recent_answer(message, user_info, play_fin, gamemode, answer_type, tries_count)

    async def create_recent_answer(self, message: Message, user_info, play_info, gamemode, answer_type, tries_count):
        answer = ''
        play_statistics = play_info['statistics']
        beatmap = await self.osuAPI.get_beatmap(play_info['beatmap']['id'])

        header = '{} {} play for {}:\n'.format(answer_type, osu_utils.beautify_mode_text(gamemode), user_info['username'])
        answer += header

        mods = ''.join(play_info['mods']) if play_info['mods'] else 'NoMod'
        title = '{} [{}]+{} [{}{}]\n'.format(
            beatmap['beatmapset']['title'], beatmap['version'], mods,
            beatmap['difficulty_rating'], emoji.emojize(":star:"))
        title_fin = hlink(title, beatmap['url'])
        answer += title_fin

        filepath = await self.nerinyanAPI.download_osu_file(beatmap=beatmap)

        text = ''
        rank = '> {} '.format(play_info['rank'])
        if 'F' in play_info['rank']:
            rank += '({:0.2f}%) '.format(await osu_utils.get_map_completion(play_info, filepath))
        text += rank

        play_pp = play_info['pp'] if play_info['pp'] is not None else await osu_utils.calculate_pp(mods=mods, filepath=filepath,
                                                                                                   play_info=play_info)
        pp_text = '> {:0.2f}PP '.format(play_pp)
        if gamemode == 'osu' and (play_statistics['count_miss'] >= 1 or
                                  ('S' in play_info['rank'] and play_info['max_combo'] <= beatmap['max_combo'] * 0.9)):
            fc_pp = await osu_utils.calculate_pp_fc(mods=mods, filepath=filepath, play_info=play_info)
            fc_acc = await osu_utils.fc_accuracy(play_statistics)
            pp_text += '({:0.2f}PP for {:0.2f}% FC) '.format(fc_pp, fc_acc)
        text += pp_text

        acc_text = '> {:0.2f}%\n'.format(play_info['accuracy'] * 100)
        text += acc_text

        score_text = '> {} '.format(play_info['score'])
        text += score_text

        combo_text = '> x{}/{} '.format(play_info['max_combo'], beatmap['max_combo'])
        text += combo_text

        hitcount_text = '> [{}/{}/{}/{}]'.format(play_statistics['count_300'], play_statistics['count_100'],
                                                 play_statistics['count_50'], play_statistics['count_miss'])
        text += hitcount_text
        text += '\n'
        answer += text

        footer = ''
        footer_tries = '> Try #{} '.format(tries_count) if tries_count else ''
        footer += footer_tries

        date = datetime.datetime.fromisoformat(play_info['created_at'][:-1])
        footer_date = '> {}'.format(date.strftime('%d.%m.%Y %H:%M'))
        footer += footer_date

        answer += footer

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

        final_gamemode = 'osu'
        for gamemode in gamemodes:
            if gamemodes[gamemode]:
                final_gamemode = str(gamemode)

        return outputs, final_gamemode

    @staticmethod
    def _option_parser_recent(inputs):
        option_parser = OptionParser()
        option_parser.add_option(opt='b', opt_value='best', opt_type=None, default=False)
        option_parser.add_option(opt='ps', opt_value='pass', opt_type=None, default=None)
        option_parser.add_option(opt='i', opt_value='index', opt_type=int, default=None)
        option_parser.add_option(opt='?', opt_value='search', opt_type=str, default=None)
        option_parser.add_option(opt='l', opt_value='list', opt_type=None, default=False)
        usernames, options = option_parser.parse(inputs)

        return usernames, options
