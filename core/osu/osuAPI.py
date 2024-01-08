import datetime
import glob
import os.path
from io import BytesIO
from pathlib import Path
import shutil
import zipfile

import aiofiles
import aiohttp

from core.utils.uri_builder import URIBuilder


class OsuApi(object):
    def __init__(self, official_client_id=None, official_client_secret=None):
        self.official_api_v2 = officialAPIV2(client_id=official_client_id, client_secret=official_client_secret)
        self.nerinyan_api = NerinyanAPI()

        self.api_dict = {
            'bancho': self.official_api_v2,
            'nerinyan': self.nerinyan_api
        }

    async def get_user(self, user_id, mode='osu', api='bancho'):
        api_obj = self.api_dict[api]
        res = await api_obj.get_user(user_id, mode=mode)
        return res

    async def get_user_recent(self, user_id, mode='osu',
                              limit=50, api='bancho', include_fails=1):
        api_obj = self.api_dict[api]
        res = await api_obj.get_user_recent(user=user_id, mode=mode, limit=limit, include_fails=include_fails)
        return res

    async def get_user_best(self, user_id, mode='osu',
                            limit=100, api='bancho'):
        api_obj = self.api_dict[api]
        res = await api_obj.get_user_best(user=user_id, mode=mode, limit=limit)
        return res

    async def get_user_firsts(self, user_id, mode='osu',
                              limit=100, api='bancho'):
        api_obj = self.api_dict[api]
        res = await api_obj.get_user_firsts(user=user_id, mode=mode, limit=limit)
        return res

    async def get_user_recent_activity(self, user_id, limit=50, api='bancho'):
        api_obj = self.api_dict[api]
        res = await api_obj.get_user_recent_activity(user_id=user_id, limit=limit)
        return res

    async def get_user_beatmaps(self, user_id, bmp_type, limit=50, offset=0, api='bancho'):
        api_obj = self.api_dict[api]
        res = await api_obj.get_user_beatmaps(user_id=user_id, bmp_type=bmp_type, limit=limit, offset=offset)
        return res

    async def get_user_url(self, user_id, api='bancho'):
        api_obj = self.api_dict[api]
        user_url = api_obj.user_url.format(user_id)
        return user_url

    async def get_beatmap(self, bmap_id, api='bancho'):
        api_obj = self.api_dict[api]
        res = await api_obj.get_beatmap(bmap_id=bmap_id)
        return res

    async def download_beatmap(self, beatmap_info, api='nerinyan'):
        api_obj = self.api_dict[api]
        filepath = await api_obj.download_osu_file(beatmap=beatmap_info)
        return filepath


class officialAPIV2(object):
    def __init__(self, client_id, client_secret):
        self.name = "Bancho"
        self.base = "https://osu.ppy.sh/api/v2/{}"
        self.user_url = "https://osu.ppy.sh/users/{}"
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expire = None

    # пользователь
    async def get_user(self, user, mode):
        uri_base = f'users/{user}/{mode}'
        uri_builder = URIBuilder(uri_base)
        uri = self.base.format(uri_builder.get_uri())
        res = await self.fetch(uri)
        return res

    async def get_user_recent(self, user,
                              include_fails=1, mode='osu', limit=50, offset=0):
        uri_base = f'users/{user}/scores/recent?'

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('include_fails', include_fails)
        uri_builder.add_parameter('mode', mode)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    async def get_user_best(self, user, mode='osu', limit=100, offset=0):
        uri_base = f'users/{user}/scores/best?'

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('mode', mode)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    async def get_user_firsts(self, user_id, mode='osu', limit=50, offset=0):
        uri_base = f'users/{user_id}/scores/firsts?'

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('mode', mode)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    async def get_user_recent_activity(self, user_id, limit=50, offset=0):
        uri_base = f'users/{user_id}/recent_activity?'
        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    async def get_user_beatmaps(self, user_id, limit=50,
                                offset=0, bmp_type='ranked'):
        uri_base = f'users/{user_id}/beatmapsets/{bmp_type}?'

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    # карты
    async def get_beatmap(self, bmap_id):
        uri_base = f'beatmaps/{bmap_id}?'

        url = self.base.format(uri_base)

        res = await self.fetch(url)

        return res

    async def get_beatmapset(self, bmapset_id):
        uri_base = f'beatmapsets/{bmapset_id}?'

        url = self.base.format(uri_base)

        res = await self.fetch(url)

        return res

    # запросы
    async def get_token(self):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
            'scope': 'public'
        }
        uri = "https://osu.ppy.sh/oauth/token"

        res = await self.post(uri, payload, get_token=True)

        self.token = res['access_token']
        self.token_expire = datetime.datetime.now().timestamp() + int(res['expires_in'])

    async def fetch(self, uri):
        current_time = datetime.datetime.now().timestamp()
        if not self.token or current_time > self.token_expire:
            await self.get_token()

        payload = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }

        async with aiohttp.ClientSession(headers=payload) as session:
            async with session.get(uri) as res:
                return await res.json()

    async def post(self, uri, data, get_token=False):
        if not get_token:
            current_time = datetime.datetime.now().timestamp()
            if not self.token or current_time > self.token_expire:
                await self.get_token()

            payload = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.token}'
            }
        else:
            payload = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }

        async with aiohttp.ClientSession(headers=payload) as session:
            async with session.post(uri, json=data) as res:
                return await res.json()


class NerinyanAPI:
    def __init__(self):
        self.name = 'Nerinyan'
        self.base = 'https://api.nerinyan.moe/d/{}?noVideo=true&noBg=true&NoHitsound=true&NoStoryboard=true'
        self.headers = {'Content-Type': 'application/x-osu-beatmap-archive'}
        self.extract_path = os.path.join(os.getcwd(), 'core', 'osu', 'beatmaps', 'extract')
        self.beatmap_path = os.path.join(os.getcwd(), 'core', 'osu', 'beatmaps')

    async def download_osu_file(self, beatmap):
        beatmap_id = beatmap['id']
        beatmapset_id = beatmap['beatmapset_id']
        url = f'https://osu.ppy.sh/osu/{beatmap_id}'
        filepath = os.path.join(self.beatmap_path, f'{beatmap_id}.osu')

        if os.path.exists(filepath):
            return filepath

        await self.download_osz(beatmapset_id)

        if not os.path.isfile(filepath):
            osu_file = await self.download_file(url)
            async with aiofiles.open(filepath, mode='wb') as f:
                await f.write(osu_file)

        return filepath

    async def download_osz(self, beatmapset_id):
        url = self.base.format(beatmapset_id)

        shutil.rmtree(self.extract_path, ignore_errors=True)
        Path(self.extract_path).mkdir(parents=True, exist_ok=True)

        beatmap = await self.download_file(url)  # качаем мапсет как zip

        with zipfile.ZipFile(BytesIO(beatmap)) as r:  # распаковываем мапсет
            r.extractall(self.extract_path)

        for osu_file in glob.glob(os.path.join(self.extract_path, '*.osu')):  # находим все .osu файлы и итерируем по ним
            async with aiofiles.open(osu_file, 'r') as f:
                async for line in f:
                    if 'BeatmapID:' not in line:
                        continue
                    beatmap_id = str(line).split(':')[1].strip()  # находим ид карты
                    shutil.copy2(osu_file, os.path.join(self.beatmap_path, f'{beatmap_id}.osu')) # переимеовываем файл и кидаем в папку с картами
                    break

    async def download_file(self, url):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as res:
                if res.ok:
                    return await res.read()

