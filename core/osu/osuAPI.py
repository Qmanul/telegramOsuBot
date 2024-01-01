import datetime
import glob
import os.path
from pathlib import Path
import shutil
import zipfile

import aiofiles
import aiohttp

from core.utils.uri_builder import URIBuilder


class OsuApi(object):
    def __init__(self, official_client_id=None, official_client_secret=None):
        self.official_api_v2 = officialAPIV2(client_id=official_client_id, client_secret=official_client_secret)
        self.beatmap_download_url = 'https://api.nerinyan.moe/d/{}?noVideo=true&noBg=true&NoHitsound=true&NoStoryboard=true'

        self.api_dict = {
            'bancho': self.official_api_v2,
            'nerinyan': self.nerinyan_api
        }

    async def get_user(self, user_id, mode=0, api='bancho'):
        api_obj = self.get_api(api)
        res = await api_obj.get_user(user_id, mode=mode)
        return res

    async def get_user_recent(self, user_id, mode=0,
                              limit=50, api='bancho'):
        api_obj = self.get_api(api)
        res = await api_obj.get_user_recent(user=user_id, mode=mode, limit=limit)
        return res

    async def get_user_best(self, user_id, mode=0,
                            limit=100, api='bancho'):
        api_obj = self.get_api(api)
        res = await api_obj.get_user_best(user=user_id, mode=mode, limit=limit)
        return res

    async def get_user_firsts(self, user_id, mode=0,
                              limit=100, api='bancho'):
        api_obj = self.get_api(api)
        res = await api_obj.get_user_firsts(user=user_id, mode=mode, limit=limit)
        return res

    async def get_user_recent_activity(self, user_id, limit=50, api='bancho'):
        api_obj = self.get_api(api)
        res = await api_obj.get_user_recent_activity(user_id=user_id, limit=limit)
        return res

    async def get_beatmap(self, bmap_id, api='bancho'):
        api_obj = self.get_api(api)
        res = await api_obj.get_beatmap(bmap_id=bmap_id)
        return res

    async def donwload_beatmap(self, beatmap):
        beatmap_id = beatmap['id']

    async def download_osz_file(self, beatmap_id):
        url = self.beatmap_download_url.format(beatmap_id)

    def get_api(self, api_name):
        return self.api_dict[api_name]


class officialAPIV2(object):
    def __init__(self, client_id, client_secret):
        self.name = "Bancho"
        self.base = "https://osu.ppy.sh/api/v2/{}"
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expire = None

    # пользователь
    async def get_user(self, user, mode):
        uri_base = 'users/{}/{}'.format(user, mode)
        uri_builder = URIBuilder(uri_base)
        uri = self.base.format(uri_builder.get_uri())
        res = await self.fetch(uri)
        return res

    async def get_user_recent(self, user,
                              include_fails=True, mode=0, limit=50, offset=0):
        uri_base = 'users/{}/scores/recent?'.format(user)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('include_fails', include_fails)
        uri_builder.add_parameter('mode', mode)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    async def get_user_best(self, user, mode=0, limit=100, offset=0):
        uri_base = 'users/{}/scores/best?'.format(user)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('mode', mode)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    async def get_user_firsts(self, user_id, mode=0, limit=50, offset=0):
        uri_base = 'users/{}/scores/firsts?'.format(user_id)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('mode', mode)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    async def get_user_recent_activity(self, user_id, limit=50, offset=0):
        uri_base = 'users/{}/recent_activity?'.format(user_id)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    async def get_user_beatmaps(self, user_id, limit=50,
                                offset=0, bmap_type='ranked'):
        uri_base = 'users/{user}/beatmapsets/{type}?'.format(user=user_id, type=bmap_type)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.get_uri())

        res = await self.fetch(url)

        return res

    # карты
    async def get_beatmap(self, bmap_id):
        uri_base = 'beatmaps/{beatmap}?'.format(beatmap=bmap_id)

        url = self.base.format(uri_base)

        res = await self.fetch(url)

        return res

    async def get_beatmapset(self, bmapset_id):
        uri_base = 'beatmapsets/{beatmapset}?'.format(beatmapset=bmapset_id)

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
            'Authorization': 'Bearer {}'.format(self.token),
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
                'Authorization': 'Bearer {}'.format(self.token)
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

    async def download_osz(self, beatmapset_id):
        url = self.base.format(beatmapset_id)
        zip_filepath = os.path.join(self.extract_path, 'ext_beatmapset.zip'.format(beatmapset_id))

        # пересоздаём папку для распаковки
        shutil.rmtree(self.extract_path, ignore_errors=True)
        Path(self.extract_path).mkdir(parents=True, exist_ok=True)

        await self.download_file(url, zip_filepath)  # качаем мапсет как zip

        with zipfile.ZipFile(zip_filepath, 'r') as r:  # распаковываем мапсет
            r.extractall(self.extract_path)

        for osu_file in glob.glob(os.path.join(self.extract_path, '*.osu')):  # находим все .osu файлы и итерируем по ним
            async with aiofiles.open(osu_file, 'r') as f:
                async for line in f:
                    if 'BeatmapID:' not in line:
                        continue
                    beatmap_id = str(line).split(':')[1].strip()  # находим ид карты
                    shutil.copy2(osu_file, os.path.join(self.beatmap_path, '{}.osu'.format(beatmap_id)))  # переимеовываем файл и кидаем в папку с картами
                    break

    async def download_file(self, url, path):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as res:
                if res.status == 200:
                    async with aiofiles.open(path, mode='wb') as f:
                        await f.write(await res.read())

