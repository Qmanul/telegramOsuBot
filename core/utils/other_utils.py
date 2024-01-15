import io
from datetime import datetime
from PIL import Image
from dateutil.relativedelta import relativedelta


async def get_image_by_url(url):

    from aiogram.client.session import aiohttp

    async with aiohttp.ClientSession(auto_decompress=False) as session:
        async with session.get(url) as res:
            return Image.open(io.BytesIO(await res.read())).convert('RGBA')


# credits to some stranger from stack overflow
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
        result.append(f'{date_delta.years} Year{"s"[:date_delta.years^1]}')
    if date_delta.months:
        result.append(f'{date_delta.months} Month{"s"[:date_delta.months^1]}')
    if date_delta.days:
        result.append(f'{date_delta.days} Day{"s"[:date_delta.days^1]}')
    if date_delta.hours:
        result.append(f'{date_delta.hours} Hour{"s"[:date_delta.hours^1]}')
    if date_delta.minutes:
        result.append(f'{date_delta.minutes} Minute{"s"[:date_delta.minutes^1]}')
    if not result:
        return 'Just Now'
    result = ' '.join(result[:2]) + ' Ago'
    return result
