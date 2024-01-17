import io
import os

import scipy.cluster
import sklearn.cluster
import numpy
from PIL import ImageFilter, Image, ImageEnhance, ImageDraw, ImageFont
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
        'play_combo': play_info['max_combo'],
        'max_combo': map_info['max_combo']
    }
    accuracy = round(play_info['accuracy'] * 100, 2)
    hit_count = play_info['statistics']
    play_date = f'@ {datetime.fromisoformat(play_info["created_at"][:-1]).strftime("%Y-%m-%d %H:%M:%S")} UTC'
    pp = {
        'play_pp': round(play_info['pp']) if play_info['pp'] else map_info['pp'],
        'fc_pp': map_info['fc_pp']
    }
    map_stats = {
        'star_rating': map_info['star_rating'],
        'bpm': map_info['bpm'],
        'ar': map_info['ar'],
        'od': map_info['od'],
        'hp': map_info['hp'],
        'cs': map_info['cs'],
    }
    mapper = play_info['beatmapset']['creator']

    size = (0, 0, 1500, 500)
    map_bg = Image.open(io.BytesIO(map_bg)).convert('RGBA')
    main_colors = await dominant_colors(map_bg)
    scale = max(size[2] / map_bg.width, size[3] / map_bg.height)
    background = await banner_enhancer(map_bg, scale, size, brightness_scale=.7)
    version_icon = await osu_utils.get_version_icon(map_info['star_rating'], play_info['mode'])

    font_main_path = os.path.join(os.getcwd(), 'core', 'osu', 'fonts', 'Asimov.ttf')
    img_path = os.path.join(os.getcwd(), 'core', 'osu', 'images')

    #  draw boxes
    boxes_canvas = Image.new('RGBA', (size[2], size[3]), color=(50, 50, 50, 210))
    draw_rectangles = ImageDraw.Draw(boxes_canvas)
    rectangles_color = (40, 40, 40, 210)

    rectangles = [(26, 15, 1130, 120), (26, 135, 830, 485), (1145, 15, 1500, 485)]
    for rectangle_coordinates in rectangles:
        draw_rectangles.rectangle(rectangle_coordinates, fill=rectangles_color)

    draw_rectangles.rectangle((0, 0, 25, 500), fill=main_colors[3])

    background = Image.alpha_composite(background, boxes_canvas)

    #  draw labels
    text_canvas = Image.new('RGBA', (size[2], size[3]), color=(0, 0, 0, 0))
    draw_text = ImageDraw.Draw(text_canvas)
    font_large = ImageFont.truetype(font_main_path, 60)
    font_normal = ImageFont.truetype(font_main_path, 40)
    font_small = ImageFont.truetype(font_main_path, 30)
    font_xsmall = ImageFont.truetype(font_main_path, 18)
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

    #  title
    text_canvas, _ = await draw_text_glow(map_title, text_canvas, (41, 18), font=font_normal)

    #  difficulty
    text_canvas.paste(version_icon, (50, 75))
    text_canvas, version_length = await draw_text_glow(version, text_canvas, (95, 70), font=font_normal)



    background = Image.alpha_composite(background, text_canvas)

    return background


async def draw_text_glow(text, image, position: tuple[float, float], font, font_clr=(255, 255, 255, 255),
                         glow_clr=(0, 0, 0, 255), blur_r=7):
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
    image = image.resize((100, 100))
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
