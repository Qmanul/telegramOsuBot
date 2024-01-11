from PIL import ImageFilter, Image, ImageEnhance
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, date
from dateutil.rrule import rrule, MONTHLY
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

    if banner.width > banner.height:
        scale_factor = graph.width / banner.width
    else:
        scale_factor = graph.height / banner.height

    banner = ImageEnhance.Brightness(
        banner.resize((round(banner.width * scale_factor), round(banner.height * scale_factor)), Image.LANCZOS).crop(
            (0, 0, graph.width, graph.height)).filter(ImageFilter.GaussianBlur(10))).enhance(.5)

    return Image.alpha_composite(banner, graph)
