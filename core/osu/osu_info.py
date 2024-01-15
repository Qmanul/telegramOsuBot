import asyncio
import io
from itertools import islice
from math import ceil

import emoji
from aiogram.types import BufferedInputFile
from aiogram.utils.markdown import hlink
from flag import flag

from core.osu import osu_utils
from core.osu.osu import Osu
from core.utils import other_utils, drawing


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
        self.bytes_buffer = io.BytesIO()
        self.items_per_page = 20

    async def process_set_user(self, telegram_user, args):
        if args is None:
            return {'answer': 'No username'}
        username = args

        if username == 'NONE':
            user_update = {
                'username': None,
                'user_id': None
            }
            await self.user_db.update_user(telegram_user.id, user_update)
            return {'answer': f'{telegram_user.first_name}, your username has been removed.'}

        osu_user = None

        for gamemode in self.gamemodes:
            osu_user = await self.osuAPI.get_user(username, gamemode)
            if osu_user:
                break
            await asyncio.sleep(.5)

        if not osu_user:
            return f"{username} doesn't exists"

        if not await self.user_db.check_user_exists(telegram_user.id):
            await self.user_db.create_new_user(telegram_user, osu_user)
            answer_type = 'linked'
        else:
            user_update = {
                'user_id': osu_user['id'],
                'username': osu_user['username']
            }
            await self.user_db.update_user(telegram_user.id, user_update)
            answer_type = 'edited'
        return {'answer': f'{telegram_user.first_name}, your username has been {answer_type} to `{osu_user["username"]}`.'}

    async def process_user_info(self, telegra_user, args, gamemode):
        processed_options = await self.process_user_inputs(telegra_user, args, 'user_info')
        try:
            username, option_gamemode, options, _ = processed_options
        except ValueError:
            return {'answer': processed_options, }

        gamemode = option_gamemode if option_gamemode else gamemode
        user_info = await self.osuAPI.get_user(username, gamemode)
        try:
            user_info['error']
            return {'answer': f'{username} was not found'}
        except KeyError:
            pass

        if options['recent']:
            return await self.user_info_recent_answer(user_info, gamemode)

        if options['beatmaps']:
            bmp_type = options['beatmaps']
            return

        if options['mostplayed']:
            return await self.user_info_most_played_answer(user_info, options['page'])

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
            plot.save(self.bytes_buffer, format='PNG')
            self.bytes_buffer.seek(0)
            img_byte_arr = self.bytes_buffer.getvalue()
            self.bytes_buffer.truncate(0)
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

    async def user_info_most_played_answer(self, user_info, page):
        bmp_list = await self.osuAPI.get_user_beatmaps(user_info['id'], 'most_played')
        answer = ''
        header = f'{flag(user_info["country_code"])} Most played beatmaps for Qmanul {user_info["username"]}:\n'
        answer += header
        max_page = ceil(len(bmp_list) / self.items_per_page)
        try:
            page = self.items_per_page * (page - 1)
        except TypeError:
            page = 0

        if page // self.items_per_page > max_page:
            return {'answer': f'{user_info["username"]} has no recent plays with those options.'}

        for bmp in islice(bmp_list, page, page + min(len(bmp_list) - page, self.items_per_page)):
            temp_title = f'{bmp["beatmapset"]["artist"][:18]} - {bmp["beatmapset"]["title"][:18]} [{bmp["beatmap"]["version"][:18]}] '
            title = hlink(temp_title, f'https://osu.ppy.sh/b/{bmp["beatmap_id"]}')
            playcount = f'▶{bmp["count"]}\n'
            answer += title + playcount

        footer = f'On osu! Bancho Server | Page {page // self.items_per_page + 1} of {max_page}'
        answer += footer
        return {'answer': answer, 'disable_web_page_preview': True}
