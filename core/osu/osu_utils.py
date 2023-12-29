import pyttanko


def beautify_mode_text(gamemode: str):
    tdict = {
        'osu': 'osu! Standard',
        'taiko': 'osu! Taiko',
        'fruits': 'Cath the Beat',
        'mania': 'osu! Mania'
    }
    return tdict[gamemode]


def mod_to_number(passed_mods: list):
    passed_mods = [x.upper() for x in passed_mods]
    res = 0
    mods = ['NF', 'EZ', 'TD', 'HD', 'FILLER', 'HR', 'DT', 'FILLER', 'HT', 'NC', 'FL', 'FILLER', 'SO']

    for mod in passed_mods:
        if mod not in mods:
            continue
        res += 1 << mods.index(mod)
    return int(res)


def calculate_pp(bmp, mods=0):
    if isinstance(mods, list):
        mods = mod_to_number(mods)
    stars = pyttanko.diff_calc().calc(bmap=bmp, mods=mods)
    pp, _, _, _, _ = pyttanko.ppv2()
    return True