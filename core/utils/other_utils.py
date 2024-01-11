import io
from PIL import Image


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
    return