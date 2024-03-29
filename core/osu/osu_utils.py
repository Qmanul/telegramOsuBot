import copy
import os.path

import emoji
import oppadc
from PIL import Image
from aiogram.utils.markdown import hlink

from core.utils import other_utils


async def get_full_play_info(filepath, play_info: dict):
    bmp = oppadc.OsuMap(file_path=filepath)
    info = await fix_keys(play_info)
    res = {}
    mods = ''.join(play_info['mods']) if play_info['mods'] else 'NoMod'

    speed_scale = 1.0
    if any(mod in mods for mod in ['DT', 'NC']):
        speed_scale *= 1.5
    if 'HT' in mods:
        speed_scale *= 0.75
    res['bpm'] = play_info['beatmap']['bpm'] * speed_scale

    stats = bmp.getDifficulty(Mods=mods, recalculate=True)
    res['ar'] = stats.ar
    res['cs'] = stats.cs
    res['od'] = stats.od
    res['hp'] = stats.hp

    res['max_combo'] = bmp.maxCombo()

    res['star_rating'] = round(bmp.getStats(mods).total, 2)

    max_pp = bmp.getPP(Mods=mods)
    res['max_pp'] = max_pp.total_pp

    pp = bmp.getPP(Mods=mods, combo=info['max_combo'], n300=info['count_300'],
                   n100=info['count_100'], n50=info['count_50'], misses=info['count_miss'], recalculate=True)
    res['pp'] = pp.total_pp

    if 'F' in play_info['rank']:
        completion_hits = int(info['count_50']) + int(info['count_100']) + int(info['count_300']) + int(
            info['count_miss'])

        numobj = completion_hits - 1
        timing = int(bmp.hitobjects[-1].starttime) - int(bmp.hitobjects[0].starttime)
        point = int(bmp.hitobjects[numobj].starttime) - int(bmp.hitobjects[0].starttime)
        completion = (point / timing) * 100

        res['completion'] = completion

    if info['mode'] == 'osu' and (
            info['count_miss'] >= 1 or ('S' in play_info['rank'] and play_info['max_combo'] <= bmp.maxCombo() * 0.9) or
            play_info['max_combo'] < bmp.maxCombo() // 2):
        # noinspection PyTypeChecker
        fc_pp = bmp.getPP(Mods=mods, combo=bmp.maxCombo(), n300=info['count_300'] + info['count_miss'],
                          n100=info['count_100'], n50=info['count_50'], misses=0, recalculate=True)
        res['fc_pp'] = fc_pp.total_pp

        fc_acc = ((300 * (info['count_300'] + info['count_miss']) + 100 * info['count_100'] + 50 * info['count_50']) / (
                300 * (info['count_300'] + info['count_miss'] + info['count_100'] + info['count_50'] + 0)))
        res['fc_acc'] = fc_acc * 100

    return res


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


async def create_play_info(play_info, beatmap, filepath):
    play_statistics = play_info['statistics']
    mods = ''.join(play_info['mods']) if play_info['mods'] else 'NoMod'
    map_info = await get_full_play_info(filepath, play_info)

    title = f"{beatmap['beatmapset']['title']} [{beatmap['version']}]+{mods} [{map_info['star_rating']}{emoji.emojize(':star:')}]\n"
    title_fin = hlink(title, beatmap['url'])

    text = ''
    rank = f"▸ {play_info['rank']} "

    if 'completion' in map_info:
        rank += f'({map_info["completion"]:0.2f}%) '
    text += rank

    play_pp = play_info['pp'] if play_info['pp'] is not None else map_info['pp']
    pp_text = f'▸ {play_pp:0.2f}PP '
    if 'fc_pp' in map_info:
        fc_pp, fc_acc = map_info['fc_pp'], map_info['fc_acc']
        pp_text += f'({fc_pp:0.2f}PP for {fc_acc:0.2f}% FC) '
    text += pp_text

    acc_text = f"▸ {play_info['accuracy'] * 100:0.2f}%\n"
    text += acc_text

    score_text = f"▸ {format(play_info['score'], ',')} "
    text += score_text

    combo_text = f"▸ x{play_info['max_combo']}/{beatmap['max_combo']} "
    text += combo_text

    hitcount_text = f"▸ [{play_statistics['count_300']}/{play_statistics['count_100']}/{play_statistics['count_50']}/{play_statistics['count_miss']}]\n"
    text += hitcount_text

    date = await other_utils.format_date(play_info['created_at'][:-1])
    score_date = f'{date}'

    return title_fin, text, score_date


async def process_user_info_recent_achievement(recent_info: dict, date):
    return f'▸ Unlocked the {recent_info["achievement"]["name"]} medal {date}\n'


async def process_user_info_recent_rank(recent_info: dict, date):
    map_link = f'<a href="https://osu.ppy.sh{recent_info["beatmap"]["url"]}">{recent_info["beatmap"]["title"]}</a>'
    if 'scoreRank' in recent_info.keys():
        return f'▸ ({recent_info["scoreRank"]}) Achieved #{recent_info["rank"]} on {map_link} {date}\n'
    return f'▸ Lost first on {map_link} {date}\n'


async def process_user_info_recent_beatmapset(recent_info: dict, date):
    map_link = f'<a href="https://osu.ppy.sh{recent_info["beatmapset"]["url"]}">{recent_info["beatmapset"]["title"]}</a>'
    recent_type = str(recent_info["type"].replace("beatmapset", ""))
    recent_type += 'ed' if recent_info["type"][-1] == 'd' else 'd'
    return f'▸ {recent_type} beatmapset {map_link} {date}\n'


async def process_user_info_recent_user_support(recent_info: dict, date):
    if 'first' in recent_info["type"].lower():
        return f'Has bought osu!supporter for the first time {date}\n'
    elif 'gift' in recent_info["type"].lower():
        return f'Has received the gift of osu!supporter {date}\n'
    else:
        return f'Has bought osu!supporter again {date}\n'


async def add_index_key(play_list):
    for index, play_info in enumerate(play_list):
        play_info['index'] = index


async def process_user_info_recent_usernameChange(recent_info: dict, date):
    return


async def get_version_icon(star_rating, gamemode):
    if star_rating > 9:
        star_rating = 9.0
    else:
        star_rating = round(star_rating, 1)
    path = os.path.join(os.getcwd(), 'core', 'osu', 'images', 'diff_icons', gamemode, f'{star_rating}.png')
    return Image.open(path).convert('RGBA').resize((40, 40), Image.LANCZOS)


async def get_grade_icon(grade):
    path = os.path.join(os.getcwd(), 'core', 'osu', 'images', 'grade_icons', f'{str(grade).lower()}.png')
    return await other_utils.resize_image(Image.open(path).convert('RGBA'), (240, 240))


async def get_mod_icon(mod):
    path = os.path.join(os.getcwd(), 'core', 'osu', 'images', 'mod_icons', f'{str(mod).lower()}.png')
    return await other_utils.resize_image(Image.open(path).convert('RGBA'), (75, 75))


async def get_hit_icon(hit):
    path = os.path.join(os.getcwd(), 'core', 'osu', 'images', 'hit_icons', f'{str(hit).lower()}.png')
    return await other_utils.resize_image(Image.open(path).convert('RGBA'), (80, 47))
