from itertools import islice
from math import ceil

from aiogram.enums import ParseMode
from aiogram.filters import CommandObject
from flag import flag

from core.osu import osu_utils
from core.osu.osu import Osu


class OsuScore(Osu):
    def __init__(self):
        super().__init__()

    async def process_user_recent(self, telegram_user, args):
        processed_options = await self.process_user_inputs(telegram_user, args, 'user_recent')
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
