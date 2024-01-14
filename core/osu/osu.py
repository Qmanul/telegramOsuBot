import asyncio
import io
import re
from math import ceil

import emoji
from flag import flag
from itertools import islice
from aiogram.enums import ParseMode
from aiogram.filters import CommandObject
from aiogram.types import Message, BufferedInputFile
from aiogram.utils.markdown import hlink

from core.utils import drawing, other_utils
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


class OsuInfo(Osu):
    def __init__(self):
        super().__init__()
        self.recent_event_types_dict = {
            'achievement': osu_utils.process_user_info_recent_achievement,
            'rank': osu_utils.process_user_info_recent_rank,
            'rankLost': osu_utils.process_user_info_recent_rank,
            'beatmapsetApprove': osu_utils.process_user_info_recent_beatmapset,
            'beatmapsetUpdate': osu_utils.process_user_info_recent_beatmapset,
            'beatmapsetDelete': osu_utils.process_user_info_recent_beatmapset,
            'beatmapsetUpload': osu_utils.process_user_info_recent_beatmapset,
            'beatmapsetRevive': osu_utils.process_user_info_recent_beatmapset,
            'userSupportFirst': osu_utils.process_user_info_recent_userSupport,
            'userSupportGift': osu_utils.process_user_info_recent_userSupport,
            'userSupportAgain': osu_utils.process_user_info_recent_userSupport,
            'usernameChange': osu_utils.process_user_info_recent_usernameChange
        }
        self.extra_info_dict = {'previous_usernames': '▸ <b>Previously known as:</b> {}\n',
                                'playstyle': '▸ <b>Playstyle:</b> {}\n',
                                'follower_count': '▸ <b>Followers:</b> {}\n',
                                'ranked_and_approved_beatmapset_count': '▸ <b>Ranked/Approved Beatmaps:</b> {}\n',
                                'replays_watched_by_others': '▸ <b>Replays Watched By Others:</b> {}\n'
                                }

    async def process_set_user(self, message: Message, command: CommandObject):
        user = message.from_user

        if command.args is None:
            return {'answer': 'No username'}
        username = command.args

        if username == 'NONE':
            user_update = {
                'username': None,
                'user_id': None
            }
            await self.user_db.update_user(user.id, user_update)
            return {'answer': f'{user.first_name}, your username has been removed.', 'parse_mode': ParseMode.HTML}

        osu_user = None

        for gamemode in self.gamemodes:
            osu_user = await self.osuAPI.get_user(username, gamemode)
            if osu_user:
                break
            await asyncio.sleep(.5)

        if not osu_user:
            return f"{username} doesn't exists"

        if not await self.user_db.check_user_exists(user.id):
            await self.user_db.create_new_user(user, osu_user)
            answer_type = 'linked'
        else:
            user_update = {
                'user_id': osu_user['id'],
                'username': osu_user['username']
            }
            await self.user_db.update_user(user.id, user_update)
            answer_type = 'edited'
        return {'answer': f'{user.first_name}, your username has been {answer_type} to `{osu_user["username"]}`.'}

    async def process_user_info(self, message: Message, opt: CommandObject, gamemode):
        processed_options = await self.process_user_inputs(message.from_user, opt.args, 'user_info')
        try:
            username, option_gamemode, options = processed_options
        except ValueError:
            return {'answer': processed_options, }

        gamemode = option_gamemode if option_gamemode else gamemode
        user_info = await self.osuAPI.get_user(username, gamemode)
        try:
            user_info['error']
            return {'answer': f'{username} was not found', 'parse_mode': ParseMode.HTML,
                    }
        except KeyError:
            pass

        if options['recent']:
            return await self.user_info_recent_answer(user_info, gamemode)

        if options['beatmaps']:
            bmp_type = options['beatmaps']
            return

        if options['mostplayed']:
            return

        if options['detailed']:
            return await self.user_info_answer(user_info, gamemode, detailed=True)

        return await self.user_info_answer(user_info, gamemode)

    async def user_info_answer(self, user, gamemode, **kwargs):
        answer = ''
        header_temp = f'{flag(user["country_code"])} {osu_utils.beautify_mode_text(gamemode)} Profile for {user["username"]}\n'
        header = hlink(header_temp, await self.osuAPI.get_user_url(user['id']))

        text = ''
        rank = f'#{user["statistics"]["global_rank"]}' if user['statistics']['global_rank'] else '-'
        country_rank = f"#{user['statistics']['country_rank']}" if user['statistics']['country_rank'] else ''
        text_rank = f"▸ <b>Bancho Rank:</b> {rank} ({user['country_code']}{country_rank})\n"
        text += text_rank

        peak_rank_date = await other_utils.format_date(user['rank_highest']['updated_at'][:-1])
        text_peak_rank = f"▸ <b>Peak Rank:</b> #{user['rank_highest']['rank']} achived {peak_rank_date}\n"
        text += text_peak_rank

        text_level = f"▸ <b>Level:</b> {user['statistics']['level']['current']} + {user['statistics']['level']['progress']}%\n"
        text += text_level

        text_pp_accuracy = f"▸ <b>PP:</b> {user['statistics']['pp']:0.2f} <b>Acc:</b> {user['statistics']['hit_accuracy']:0.2f}%\n"
        text += text_pp_accuracy

        text_playcount = f"▸ <b>Playcount:</b> {user['statistics']['play_count']} ({round(user['statistics']['play_time'] / 3600)} hrs)\n"
        text += text_playcount

        grades = user['statistics']['grade_counts']
        text_grades = f"▸ <b>Ranks:</b> SSH: {grades['ssh']} SS: {grades['ss']} SH: {grades['sh']} S: {grades['s']} A: {grades['a']}\n"
        text += text_grades

        footer = ''
        footer += emoji.emojize(':green_circle:') if user['is_online'] else emoji.emojize(':red_circle:')

        if not footer and user['last_visit']:
            visit_delta = await other_utils.format_date(user['last_visit'])
            footer += f' Last Seen {visit_delta}'
        footer += ' On osu! Bancho Server'

        if 'detailed' in kwargs:
            recent_list = await self.osuAPI.get_user_recent_activity(user['id'])
            if recent_list:
                text_recent = '<b>Recent events</b>\n'
                for recent_event in recent_list[:3]:
                    date = await other_utils.format_date(recent_event['created_at'][:-6])
                    text_recent += await self.recent_event_types_dict[recent_event['type']](recent_event, date)
                text += text_recent

            text_extra_info = ''
            for extra_info_value, extra_info_item in self.extra_info_dict.items():
                try:
                    if user[extra_info_value]:
                        try:
                            text_extra_info += extra_info_item.format(", ".join(user[extra_info_value]))
                        except TypeError:
                            text_extra_info += extra_info_item.format(user[extra_info_value])
                except KeyError:
                    pass

            if text_extra_info:
                text += '<b>Extra Info</b>\n'
                text += text_extra_info

            plot = await drawing.plot_profile(user)
            img_byte_arr = io.BytesIO()
            plot.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            answer += header
            answer += text
            answer += footer
            return {'answer': answer, 'photo': BufferedInputFile(img_byte_arr, filename='plot.png')}

        answer += header
        answer += text
        answer += footer
        return {'answer': answer}

    async def user_info_recent_answer(self, user, gamemode):
        recent_list = await self.osuAPI.get_user_recent_activity(user['id'])
        answer = ''

        rank = f'#{user["statistics"]["global_rank"]}' if user['statistics']['global_rank'] else '-'
        country_rank = f"#{user['statistics']['country_rank']}" if user['statistics']['country_rank'] else ''
        header_temp = (f'{flag(user["country_code"])} Recent {osu_utils.beautify_mode_text(gamemode)} Activity for '
                       f'{user["username"]} [{rank} | {user["country_code"]}{country_rank}]\n')
        header = hlink(header_temp, await self.osuAPI.get_user_url(user['id']))

        text = ''
        for recent_info in recent_list[:10]:
            date = await other_utils.format_date(recent_info['created_at'][:-6])
            text += await self.recent_event_types_dict[recent_info['type']](recent_info, date)

        footer = ''
        footer += emoji.emojize(':green_circle:') if user['is_online'] else emoji.emojize(':red_circle:')

        if not footer and user['last_visit']:
            visit_delta = await other_utils.format_date(user['last_visit'])
            footer += f' Last Seen {visit_delta}'
        footer += ' On osu! Bancho Server'

        answer += header
        answer += text
        answer += footer
        return {'answer': answer, 'disable_web_page_preview': True}


class OsuScores(Osu):
    def __init__(self):
        super().__init__()

    async def process_user_recent(self, message: Message, opt: CommandObject):
        processed_options = await self.process_user_inputs(message.from_user, opt.args, 'user_recent')
        try:
            username, option_gamemode, options = processed_options
        except ValueError:
            return {'answer': processed_options, }

        gamemode = option_gamemode if option_gamemode else 'osu'
        user_info = await self.osuAPI.get_user(username, gamemode)
        try:
            user_info['error']
            return {'answer': f'{username} was not found', 'parse_mode': ParseMode.HTML,
                    }
        except KeyError:
            pass

        include_fails = 0 if options['pass'] else 1

        if options['best']:
            play_list = await self.osuAPI.get_user_best(user_id=user_info['id'], mode=gamemode)
            await osu_utils.add_index_key(play_list)
            play_list.sort(key=lambda x: x['created_at'], reverse=True)

        else:
            play_list = await self.osuAPI.get_user_recent(user_id=user_info['id'], mode=gamemode,
                                                          include_fails=include_fails)
            if not play_list:
                return {
                    'answer': f'{user_info["username"]} has no recent plays for {osu_utils.beautify_mode_text(gamemode)}',
                }

            await osu_utils.add_index_key(play_list)

        if options['search']:
            queries = options['search'].replace('"', '').lower().split()
            temp_play_list = []
            for play_info in play_list:
                if not all(key in play_info for key in ['beatmap', 'beatmapset']):
                    play_list.remove(play_info)
                    continue
                title = (f"{play_info['beatmapset']['artist']} {play_info['beatmapset']['title']} "
                         f"{play_info['beatmapset']['creator']} {play_info['beatmap']['version']}").lower()
                if not set(title.split()).isdisjoint(queries):
                    temp_play_list.append(play_info)

            if not temp_play_list:
                return {
                    'answer': f'{user_info["username"]} has no recent plays for {osu_utils.beautify_mode_text(gamemode)} with those options.',
                }
            play_list = temp_play_list

        if options['list']:
            try:
                page = int(options['page']) - 1
            except TypeError:
                page = 0
            return await self.recent_answer_list(user_info, play_list, gamemode, page)

        if options['index']:
            try:
                play_fin = play_list[options['index'] - 1]
            except IndexError:
                return {
                    'answer': f'{user_info["username"]} has no recent plays for {osu_utils.beautify_mode_text(gamemode)} with those options.',
                }
        else:
            play_fin = play_list[0]

        if options['best']:
            answer_type = f'Top {str(play_fin["index"] + 1)}'
            tries_count = None
        else:
            answer_type = 'Recent'
            tries_count = await osu_utils.get_number_of_tries(play_list, play_fin['beatmap']['id'])

        return await self.recent_answer(user_info, play_fin, gamemode, answer_type, tries_count)

    async def recent_answer(self, user_info, play_info, gamemode, answer_type, tries_count):
        answer = ''
        beatmap = await self.osuAPI.get_beatmap(play_info['beatmap']['id'])
        filepath = await self.osuAPI.download_beatmap(beatmap_info=beatmap, api='nerinyan')
        header = f"{flag(user_info['country_code'])} {answer_type} {osu_utils.beautify_mode_text(gamemode)} Play for {user_info['username']}:\n"

        title, text, score_date = await osu_utils.create_play_info(play_info, beatmap, filepath)

        footer = ''
        footer_tries = f' Try #{tries_count} • ' if tries_count else ''
        footer += footer_tries
        footer_server = 'On osu! Bancho Server • '
        footer += footer_server
        footer += score_date

        answer += header
        answer += title
        answer += text
        answer += footer

        return {'answer': answer, }

    async def recent_answer_list(self, user_info, play_list: list, gamemode, page):

        answer = ''
        header = f'{flag(user_info["country_code"])} Recent {osu_utils.beautify_mode_text(gamemode)} Plays for {user_info["username"]}:\n'
        answer += header
        max_page = ceil(len(play_list) / 5)
        if page > max_page:
            return {
                'answer': f'{user_info["username"]} has no recent plays for {osu_utils.beautify_mode_text(gamemode)} with those options.',
            }
        page = 5 * page

        for play_info in islice(play_list, page, page + min(len(play_list) - page, 5)):
            beatmap = await self.osuAPI.get_beatmap(play_info['beatmap']['id'])
            filepath = await self.osuAPI.download_beatmap(beatmap_info=beatmap, api='nerinyan')
            title, text, score_date = await osu_utils.create_play_info(play_info, beatmap, filepath)

            answer += f'{play_info["index"] + 1}) '
            answer += title
            answer += text
            answer += f'▸ Score Set {score_date}\n'

        footer = f'On osu! Bancho Server | Page {page // 5 + 1} of {max_page}'
        answer += footer
        return {'answer': answer, 'parse_mode': ParseMode.HTML,
                'disable_web_page_preview': True}  # ,'keyboard': pagination_kb.get_pagination_kb(data=data)
