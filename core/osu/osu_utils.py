import copy
import oppadc


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
