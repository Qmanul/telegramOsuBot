import io
import os

import scipy.cluster
import sklearn.cluster
import numpy
from PIL import ImageFilter, Image, ImageEnhance, ImageDraw, ImageFont, UnidentifiedImageError
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, date
from dateutil.rrule import rrule, MONTHLY

from core.osu import osu_utils
from core.utils import other_utils


async def plot_profile(user):
    color_main = '#e81e63'
    color_secondary = '#2eeaa9'

    start_date = date.fromisoformat(user['monthly_playcounts'][0]['start_date'])
    last_date = date.fromisoformat(user['monthly_playcounts'][-1]['start_date'])
    all_dates = {day.date(): 0 for day in rrule(MONTHLY, dtstart=start_date, until=last_date)}

    monthly_playcount = all_dates | {date.fromisoformat(item['start_date']): int(item['count']) for item in
                                     user['monthly_playcounts']}
    replays_watched = all_dates | {date.fromisoformat(item['start_date']): int(item['count']) for item in
                                   user['replays_watched_counts']}

    rank_history_dates = [datetime.utcnow().date() - timedelta(days=x) for x in range(90, 0, -1)]
    rank_history_counts = user['rank_history']['data']

    fig, axs = plt.subplots(nrows=2, ncols=1, figsize=(16, 8))

    # rank axes
    rank_ax = axs[0]
    rank_ax.plot(rank_history_dates, rank_history_counts, 'o', ls='-', linewidth=3, markevery=slice(0, -1, 3),
                 color=color_main, label='Rank (90 days)')

    for n in range(10):
        rank_ax.plot(rank_history_dates, rank_history_counts, marker='o', ls='-', linewidth=2 + 1.05 * n,
                     color=color_main, alpha=0.03, markevery=slice(0, -1, 3))

    rank_ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))

    rank_history_counts_range = max(rank_history_counts) - min(rank_history_counts)
    rank_ax.set_ylim(min(rank_history_counts) - round(rank_history_counts_range * .1),
                     max(rank_history_counts) + round(rank_history_counts_range * .1))
    rank_ax.fill_between(rank_history_dates, rank_history_counts, max(rank_history_counts), alpha=.1, color=color_main)
    rank_ax.invert_yaxis()

    rank_ax.grid(True, linestyle='-', linewidth=1, axis='y', color='w')
    rank_ax.set_frame_on(False)
    rank_ax.tick_params(axis='x', colors='w', labelsize=20)
    rank_ax.tick_params(axis='y', colors=color_main, labelsize=20)
    rank_ax.legend(loc=0)

    # replays axis
    replays_ax = axs[1]
    ln1 = replays_ax.plot(*zip(*replays_watched.items()), 'o', ls='-', linewidth=2, color=color_main,
                          label='Replays watched')
    for n in range(10):
        replays_ax.plot(*zip(*replays_watched.items()), marker='o', ls='-', linewidth=2 + 1.05 * n,
                        color=color_main, alpha=0.03)

    replays_ax.fill_between(*zip(*replays_watched.items()), alpha=.1, color=color_main)
    replays_ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
    replays_ax.set_ylim(0, round(max(replays_watched.values()) * 1.2))
    replays_ax.tick_params(axis='y', colors=color_main, labelsize=20)
    replays_ax.set_frame_on(False)

    # playcount axis
    playcount_ax = replays_ax.twinx()
    ln2 = playcount_ax.plot(*zip(*monthly_playcount.items()), 'o', ls='-', linewidth=2, color=color_secondary,
                            label='Playcount')
    for n in range(10):
        playcount_ax.plot(*zip(*monthly_playcount.items()), marker='o', ls='-', linewidth=2 + 1.05 * n,
                          color=color_secondary, alpha=0.03)

    playcount_ax.fill_between(*zip(*monthly_playcount.items()), alpha=.1, color=color_secondary)
    playcount_ax.set_frame_on(False)
    playcount_ax.set_ylim(0, round(max(monthly_playcount.values()) * 1.2))
    playcount_ax.tick_params(axis='y', colors=color_secondary, labelsize=20)
    playcount_ax.grid(True, linestyle='-', linewidth=1, axis='y', color='w')

    replays_ax.tick_params(axis='x', colors='w', labelsize=20)
    lns = ln1 + ln2
    labs = [ln.get_label() for ln in lns]
    playcount_ax.legend(lns, labs, loc=0)

    plt.rcParams.update({'font.size': 22})
    fig.tight_layout()

    graph = await other_utils.fig2img(fig)
    banner = await other_utils.get_image_by_url(user['cover_url'])
    scale = max(graph.height / banner.height, graph.width / banner.width)
    banner = await banner_enhancer(banner, scale, (0, 0, graph.width, graph.height))

    return Image.alpha_composite(banner, graph)


# TODO
async def score_image(play_info, map_bg, map_info):
    #  gather info
    map_title = f'{play_info["beatmapset"]["artist"]} - {play_info["beatmapset"]["title"]}'
    version = play_info['beatmap']['version']
    username = play_info['user']['username']
    score = format(play_info['score'], ',')
    combo = {
        'play_combo': str(play_info['max_combo']),
        'max_combo': str(map_info['max_combo'])
    }
    accuracy = str(round(play_info['accuracy'] * 100, 2))
    hit_icons = [['300', 'geki'], ['100', 'katu'], ['50', 'miss']]
    hit_count = [[str(play_info['statistics'][f'count_{hit_pair[0]}']), str(play_info['statistics'][f'count_{hit_pair[1]}'])] for hit_pair in hit_icons]
    play_date = f' {datetime.fromisoformat(play_info["created_at"][:-1]).strftime("%Y-%m-%d %H:%M:%S")} UTC'
    pp = {
        'play_pp': str(round(play_info['pp'])) if play_info['pp'] else str(round(map_info['pp'])),
        'fc_pp': str(round(map_info['fc_pp']))
    }
    map_stats = {
        'star_rating': str(round(map_info['star_rating'], 1)),
        'bpm': str(int(map_info['bpm'])),
        'ar': str(round(map_info['ar'], 1)),
        'od': str(round(map_info['od'], 1)),
        'hp': str(round(map_info['hp'], 1)),
        'cs': str(round(map_info['cs'], 1))
    }
    mapper = play_info['beatmapset']['creator']
    mods = play_info['mods']

    size = (0, 0, 1500, 500)
    try:
        map_bg = Image.open(io.BytesIO(map_bg)).convert('RGBA')
    except UnidentifiedImageError:
        map_bg = await other_utils.get_image_by_url(f'https://beatconnect.io/bg/{play_info["beatmap"]["beatmapset_id"]}/{play_info["beatmap"]["id"]}')
    dom_colors = await dominant_colors(map_bg)
    color_secondary = (100, 100, 100, 200)
    color_main = (255, 255, 255, 255)
    scale = max(size[2] / map_bg.width, size[3] / map_bg.height)
    background = await banner_enhancer(map_bg, scale, size, brightness_scale=.7)
    version_icon = await osu_utils.get_version_icon(map_info['star_rating'], play_info['mode'])
    grade_icon = await osu_utils.get_grade_icon(play_info['rank'])

    font_main_path = os.path.join(os.getcwd(), 'core', 'osu', 'fonts', 'Asimov.ttf')
    symbol_font_path = os.path.join(os.getcwd(), 'core', 'osu', 'fonts', 'Symbola.ttf')

    #  draw boxes
    boxes_canvas = Image.new('RGBA', (size[2], size[3]), color=(50, 50, 50, 210))
    draw_rectangles = ImageDraw.Draw(boxes_canvas)
    rectangles_color = (40, 40, 40, 210)

    rectangles = [(26, 15, 1130, 120), (26, 135, 830, 485), (1145, 15, 1500, 485)]
    for rectangle_coordinates in rectangles:
        draw_rectangles.rectangle(rectangle_coordinates, fill=rectangles_color)

    draw_rectangles.rectangle((0, 0, 25, 500), fill=dom_colors[0])

    #  draw labels
    text_canvas = Image.new('RGBA', (size[2], size[3]), color=(0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_canvas)
    font_xlarge = ImageFont.truetype(font_main_path, 70)
    font_large = ImageFont.truetype(font_main_path, 60)
    font_normal = ImageFont.truetype(font_main_path, 40)
    font_small = ImageFont.truetype(font_main_path, 30)
    font_xsmall = ImageFont.truetype(font_main_path, 20)
    symbol_font = ImageFont.truetype(symbol_font_path, 60)
    font_clr = (200, 200, 200, 200)

    labels = {
        'SCORE': (40, 150),
        'COMBO': (40, 260),
        'GRAPH': (40, 370),
        'ACCURACY': (390, 150),
        'MODS': (620, 150),
        'PERFORMANCE': (860, 380),
        'DIFFICULTY': (1160, 215),
        'AR': (1160, 315),
        'OD': (1322, 315),
        'HP': (1160, 380),
        'CS': (1322, 380)
    }
    for label_text, label_coordinates in labels.items():
        draw_text.text(label_coordinates, label_text, font=font_xsmall, fill=font_clr)

    test_temp = []
    #  title
    if len(map_title) >= 60:
        map_title = f'{map_title[:55]}...'
    test_temp += [map_title, (41, 18), font_normal, color_main]

    #  difficulty
    if len(version) >= 40:
        version = f'{version[:35]}...'
    test_temp += [version, (95, 70), font_normal, dom_colors[2]]
    test_temp += ['played by', (100 + draw_text.textlength(version, font_normal), 70), font_normal, color_secondary]
    test_temp += [username, (105 + draw_text.textlength(version, font_normal) + draw_text.textlength('played by', font_normal), 70), font_normal, dom_colors[2]]

    #  score
    test_temp += [score, (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(score, text_canvas, (40, 170), font=font_large)

    #  combo
    test_temp += [combo['play_combo'], (41, 18), font_normal]
    text_canvas, temp_text_length = await draw_text_glow(combo['play_combo'], text_canvas, (40, 280), font=font_large)
    test_temp += [f"/{combo['max_combo']}", (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(f"/{combo['max_combo']}", text_canvas, (40 + temp_text_length, 310),
                                          font=font_small)

    #  accuracy
    test_temp += [accuracy, (41, 18), font_normal]
    text_canvas, temp_text_length = await draw_text_glow(accuracy, text_canvas, (390, 170), font=font_large)
    test_temp += [' %', (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(' %', text_canvas, (390 + temp_text_length, 200), font=font_small)

    #  hit text
    temp_offset = 0
    for hit_pair in hit_count:
        test_temp += [hit_pair[0], (41, 18), font_normal]
        text_canvas, _ = await draw_text_glow(hit_pair[0], text_canvas, (480, 245 + temp_offset), font=font_normal)
        test_temp += [hit_pair[1], (41, 18), font_normal]
        text_canvas, _ = await draw_text_glow(hit_pair[1], text_canvas, (690, 240 + temp_offset), font=font_normal)
        temp_offset += 62

    #  date
    test_temp += ['@', (41, 18), font_normal]
    text_canvas, temp_text_length = await draw_text_glow('@', text_canvas, (390, 444), font=font_xsmall,
                                                         font_clr=color_secondary)
    test_temp += [play_date, (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(play_date, text_canvas, (390 + temp_text_length, 445), font=font_xsmall,
                                          font_clr=dom_colors[2])

    #  pp
    test_temp += [pp['play_pp'], (41, 18), font_normal]
    text_canvas, temp_text_length = await draw_text_glow(pp['play_pp'], text_canvas, (860, 410), font=font_xlarge,
                                                         font_clr=dom_colors[3])
    test_temp += [f'/{pp["fc_pp"]} PP', (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(f'/{pp["fc_pp"]} PP', text_canvas, (860 + temp_text_length, 450),
                                          font=font_small)

    # map stats
    test_temp += [map_stats['star_rating'], (41, 18), font_normal]
    text_canvas, temp_text_length = await draw_text_glow(map_stats['star_rating'], text_canvas, (1160, 240),
                                                         font=font_large, font_clr=dom_colors[2])
    test_temp += ['★', (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow('★', text_canvas, (1160 + temp_text_length, 250), font=symbol_font,
                                          font_clr=dom_colors[2])

    test_temp += [map_stats['bpm'], (41, 18), font_normal]
    text_canvas, temp_text_length = await draw_text_glow(map_stats['bpm'], text_canvas, (1322, 240), font=font_large)
    test_temp += [' BPM', (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(' BPM', text_canvas, (1322 + temp_text_length, 265), font=font_small)

    test_temp += [map_stats['ar'], (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(map_stats['ar'], text_canvas, (1200, 307), font=font_large)
    test_temp += [map_stats['od'], (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(map_stats['od'], text_canvas, (1362, 307), font=font_large)
    test_temp += [map_stats['hp'], (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(map_stats['hp'], text_canvas, (1200, 372), font=font_large)
    test_temp += [map_stats['cs'], (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(map_stats['cs'], text_canvas, (1362, 372), font=font_large)

    test_temp += ['By ', (41, 18), font_normal]
    text_canvas, temp_text_length = await draw_text_glow('By ', text_canvas, (1160, 445), font=font_small,
                                                         font_clr=color_secondary)
    test_temp += [mapper, (41, 18), font_normal]
    text_canvas, _ = await draw_text_glow(mapper, text_canvas, (1160 + temp_text_length, 445), font=font_small,
                                          font_clr=dom_colors[2])

    #  paste images
    img_canvas = Image.new('RGBA', (size[2], size[3]), color=(0, 0, 0, 0))

    #  version
    img_canvas.paste(version_icon, (50, 75))

    #  grade
    img_canvas.paste(grade_icon, (865, 135))

    #  mods
    if not mods:
        text_canvas, _ = await draw_text_glow('-', text_canvas, (620, 173), font=font_large)
    else:
        temp_offset = 0
        for mod in mods:
            icon = await osu_utils.get_mod_icon(mod)
            img_canvas.paste(icon, (612 + temp_offset, 173))
            temp_offset += 65

    #  hit icon
    temp_offset = 0
    for hit_pair in hit_icons:
        hit_icon = await osu_utils.get_hit_icon(hit_pair[0])
        img_canvas.paste(hit_icon, (390, 246 + temp_offset))
        hit_icon = await osu_utils.get_hit_icon(hit_pair[1])
        img_canvas.paste(hit_icon, (620, 246 + temp_offset))
        temp_offset += 62

    #  thumbnail
    thumbnail_size = (325, 187)
    thumbnail_bg = ImageEnhance.Brightness(map_bg.resize(thumbnail_size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))).enhance(.8)
    thumbnail = await other_utils.resize_image(map_bg, thumbnail_size)
    temp_offset = round((thumbnail_bg.width - thumbnail.width) / 2)
    img_canvas.paste(thumbnail_bg, (1160, 18))
    img_canvas.paste(thumbnail, (1160 + temp_offset, 18))

    background = Image.alpha_composite(background, boxes_canvas)
    background = Image.alpha_composite(background, text_canvas)
    background = Image.alpha_composite(background, img_canvas)

    return background


async def draw_text_glow(text, image, position: tuple[float, float], font, font_clr=(255, 255, 255, 255),
                         glow_clr=(0, 0, 0, 255), blur_r=5):
    text_canvas = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(text_canvas)
    draw.text(position, text, font=font, fill=glow_clr)

    text_canvas = text_canvas.filter(ImageFilter.GaussianBlur(blur_r))
    draw = ImageDraw.Draw(text_canvas)
    draw.text(position, text, font=font, fill=font_clr)

    text_length = draw.textlength(text, font)
    image = Image.alpha_composite(image, text_canvas)
    return image, text_length


async def banner_enhancer(img, scale, size, blur_radius=10, brightness_scale=.5):
    return ImageEnhance.Brightness(img.resize((round(img.width * scale) + 1, round(img.height * scale) + 1),
                                              Image.LANCZOS).crop(size).filter(
        ImageFilter.GaussianBlur(blur_radius))).enhance(
        brightness_scale)


# credits to Jacob https://stackoverflow.com/questions/3241929/python-find-dominant-most-common-color-in-an-image
async def dominant_colors(image):
    image = image.resize((10, 10), Image.LANCZOS)
    ar = numpy.asarray(image)
    shape = ar.shape
    ar = ar.reshape(numpy.prod(shape[:2]), shape[2]).astype(float)

    kmeans = sklearn.cluster.MiniBatchKMeans(
        n_clusters=5,
        init="k-means++",
        max_iter=20,
        random_state=1000,
        n_init=3
    ).fit(ar)
    codes = kmeans.cluster_centers_

    vecs, _dist = scipy.cluster.vq.vq(ar, codes)
    counts, _bins = numpy.histogram(vecs, len(codes))

    colors = []
    for index in numpy.argsort(counts)[::-1]:
        colors.append(tuple([int(code) for code in codes[index]]))
    return colors
