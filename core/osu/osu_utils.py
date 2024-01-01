import copy

import pyttanko
import oppadc


def beautify_mode_text(gamemode: str):
    mode_names = {
        'osu': 'osu! Standard',
        'taiko': 'osu! Taiko',
        'fruits': 'Cath the Beat',
        'mania': 'osu! Mania'
    }
    return mode_names[gamemode]


# pyttanko
'''
def mod_to_number(passed_mods: list):
    passed_mods = [x.upper() for x in passed_mods]
    mods = ['NF', 'EZ', 'TD', 'HD', 'FILLER', 'HR', 'DT', 'FILLER', 'HT', 'NC', 'FL', 'FILLER', 'SO']
    res = sum([1 << mods.index(mod) for mod in passed_mods if mod in mods])
    return int(res)


async def calculate_pp(bmp, mods, info=None):
    if mods == 'NoMod':
        mods = 0
    else:
        mods = mod_to_number(mods)

    stars = pyttanko.diff_calc().calc(bmap=bmp, mods=mods)

    if info and 'play_info' in info.keys():
        play_info = info['play_info']

        for stat, count in play_info['statistics'].items():
            play_info[stat] = count
        play_info.pop('statistics')

        pp, _, _, _, _ = pyttanko.ppv2(stars.aim, stars.speed, bmap=bmp, mods=mods,
                                       n300=play_info['count_300'], n100=play_info['count_100'], n50=play_info['count_50'],
                                       nmiss=play_info['count_miss'], combo=play_info['max_combo'])
        return pp
'''


async def calculate_pp(bmp, mods, play_info: dict, fc=False):
    play_info = copy.deepcopy(play_info)
    for stat, count in play_info['statistics'].items():
        play_info[stat] = count
    play_info.pop('statistics')
    if fc:
        play_info.update(max_combo=bmp.maxCombo(), count_300=play_info['count_300'] + play_info['count_miss'],
                         count_miss=0)

    pp = bmp.getPP(Mods=mods, combo=play_info['max_combo'], n300=play_info['count_300'],
                   n100=play_info['count_100'], n50=play_info['count_50'],
                   misses=play_info['count_miss'])
    return pp.total_pp


async def fc_accuracy(play_statistics: dict):
    play_statistics.update(count_300=play_statistics['count_300'] + play_statistics['count_miss'], count_miss=0)

    fc_acc = ((300 * play_statistics['count_300'] + 100 * play_statistics['count_100'] + 50 *
              play_statistics['count_50']) /
              (300 * (play_statistics['count_300'] + play_statistics['count_100'] + play_statistics['count_50'] +
                      play_statistics['count_miss'])))
    return fc_acc * 100
