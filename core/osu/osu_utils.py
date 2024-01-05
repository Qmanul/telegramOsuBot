import copy
from datetime import datetime

import emoji
import oppadc
from aiogram.utils.markdown import hlink


def beautify_mode_text(gamemode: str):
    mode_names = {
        'osu': 'osu! Standard',
        'taiko': 'osu! Taiko',
        'fruits': 'Catch the Beat',
        'mania': 'osu! Mania'
    }
    return mode_names[gamemode]


async def calculate_pp(filepath, mods, play_info: dict):
    bmp = oppadc.OsuMap(file_path=filepath)
    info = await fix_keys(play_info)
    pp = bmp.getPP(Mods=mods, combo=info['max_combo'], n300=info['count_300'],
                   n100=info['count_100'], n50=info['count_50'], misses=info['count_miss'])
    return pp.total_pp


async def calculate_pp_fc(filepath, mods, play_info: dict):
    bmp = oppadc.OsuMap(file_path=filepath)
    info = await fix_keys(play_info)
    pp = bmp.getPP(Mods=mods, combo=bmp.maxCombo(), n300=info['count_300'] + info['count_miss'],
                   n100=info['count_100'], n50=info['count_50'], misses=0)
    return pp.total_pp


async def fc_accuracy(play_statistics: dict):
    fc_acc = ((300 * (play_statistics['count_300'] + play_statistics['count_miss']) + 100 *
               play_statistics['count_100'] + 50 * play_statistics['count_50']) / (300 * (
            play_statistics['count_300'] + play_statistics['count_miss'] + play_statistics['count_100'] +
            play_statistics['count_50'] + 0)))
    return fc_acc * 100


async def fix_keys(play_info: dict):
    info = copy.deepcopy(play_info)
    for stat, count in info['statistics'].items():
        info[stat] = count
    info.pop('statistics')
    return info


async def get_number_of_tries(play_list, beatmap_id):
    tries_count = 0
    first_entry = False

    for play_info in play_list:
        if play_info['beatmap']['id'] == beatmap_id:
            first_entry = True
            tries_count += 1
        elif first_entry:
            break

    return tries_count


async def get_map_completion(play_info, filepath):
    bmp = oppadc.OsuMap(file_path=filepath)
    info = await fix_keys(play_info)
    completion_hits = int(info['count_50']) + int(info['count_100']) + int(info['count_300']) + int(info['count_miss'])

    numobj = completion_hits - 1
    timing = int(bmp.hitobjects[-1].starttime) - int(bmp.hitobjects[0].starttime)
    point = int(bmp.hitobjects[numobj].starttime) - int(bmp.hitobjects[0].starttime)
    completion = (point / timing) * 100

    return completion


async def create_play_info(play_info, beatmap, filepath, gamemode):
    play_statistics = play_info['statistics']
    mods = ''.join(play_info['mods']) if play_info['mods'] else 'NoMod'

    title = '{} [{}]+{} [{}{}]\n'.format(
        beatmap['beatmapset']['title'], beatmap['version'], mods,
        beatmap['difficulty_rating'], emoji.emojize(":star:"))
    title_fin = hlink(title, beatmap['url'])

    text = ''
    rank = '> {} '.format(play_info['rank'])
    if 'F' in play_info['rank']:
        rank += '({:0.2f}%) '.format(await get_map_completion(play_info, filepath))
    text += rank

    play_pp = play_info['pp'] if play_info['pp'] is not None else await calculate_pp(mods=mods,
                                                                                     filepath=filepath,
                                                                                     play_info=play_info)
    pp_text = '> {:0.2f}PP '.format(play_pp)
    if gamemode == 'osu' and (play_statistics['count_miss'] >= 1 or
                              ('S' in play_info['rank'] and play_info['max_combo'] <= beatmap['max_combo'] * 0.9)):
        fc_pp = await calculate_pp_fc(mods=mods, filepath=filepath, play_info=play_info)
        fc_acc = await fc_accuracy(play_statistics)
        pp_text += '({:0.2f}PP for {:0.2f}% FC) '.format(fc_pp, fc_acc)
    text += pp_text

    acc_text = '> {:0.2f}%\n'.format(play_info['accuracy'] * 100)
    text += acc_text

    score_text = '> {} '.format(play_info['score'])
    text += score_text

    combo_text = '> x{}/{} '.format(play_info['max_combo'], beatmap['max_combo'])
    text += combo_text

    hitcount_text = '> [{}/{}/{}/{}]\n'.format(play_statistics['count_300'], play_statistics['count_100'],
                                               play_statistics['count_50'], play_statistics['count_miss'])
    text += hitcount_text

    date = datetime.fromisoformat(play_info['created_at'][:-1])
    score_date = '{}'.format(date.strftime('%d.%m.%Y %H:%M'))

    return title_fin, text, score_date
