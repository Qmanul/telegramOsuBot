import io
from datetime import datetime

from PIL import Image
from dateutil.relativedelta import *


async def get_image_by_url(url):

    from aiogram.client.session import aiohttp

    async with aiohttp.ClientSession(auto_decompress=False) as session:
        async with session.get(url) as res:
            return Image.open(io.BytesIO(await res.read())).convert('RGBA')


async def fig2img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, transparent=True)
    buf.seek(0)
    img = Image.open(buf)
    return img


async def format_date(date_str):
    date_delta = relativedelta(datetime.utcnow(), datetime.fromisoformat(date_str))
    result = []
    if date_delta.years:
        result.append(f'{date_delta.years} Years')
    if date_delta.months:
        result.append(f'{date_delta.months} Months')
    if date_delta.days:
        result.append(f'{date_delta.days} Days')
    if date_delta.hours:
        result.append(f'{date_delta.hours} Hours')
    if date_delta.minutes:
        result.append(f'{date_delta.minutes} Minutes')
    if not result:
        return 'Just Now'
    result = ' '.join(result[:2]) + ' Ago'
    return result
