import datetime
import time
import aiohttp

from core.utils.uri_builder import URIBuilder


class OsuApi(object):
    def __init__(self, official_client_id=None, official_client_secret=None):
        self.official_api_v2 = officialAPIV2(client_id=official_client_id, client_secret=official_client_secret)

        self.api_dict = {
            'bancho': self.official_api_v2
        }

        self.last_log = time.time()
        self.request_counter = {}

    def log_request(self, request_name, api):
        if api not in self.request_counter:
            self.request_counter[api] = {}

        if request_name not in self.request_counter[api]:
            self.request_counter[api][request_name] = 0

        self.request_counter[api][request_name] += 1

    def get_api_usage(self):
        return self.request_counter

    async def get_user(self, user_id, mode=0, api='bancho'):
        request_name = 'get_user'

        res = await self.official_api_v2.get_user(user_id, mode=mode)

        self.log_request(request_name, api)
        return res

    async def get_user_recent(self, user_id, mode=0,
                              limit=50, api='bancho'):
        request_name = 'get_user_recent'
        api_obj = self.get_api(api)
        res = await api_obj.get_user_recent(user=user_id, mode=mode, limit=limit)

        self.log_request(request_name, api)
        return res

    async def get_user_best(self, user_id, mode=0,
                            limit=100, api='bancho'):
        request_name = 'get_user_best'
        api_obj = self.get_api(api)
        res = await api_obj.get_user_best(user=user_id, mode=mode, limit=limit)

        self.log_request(request_name, api)
        return res

    async def get_user_firsts(self, user_id, mode=0,
                              limit=100, api='bancho'):
        request_name = 'get_user_firsts'
        api_obj = self.get_api(api)
        res = await api_obj.get_user_firsts(user=user_id, mode=mode, limit=limit)

        self.log_request(request_name, api)
        return res

    async def get_user_recent_activity(self, user_id, limit=50, api='bancho'):
        request_name = 'get_user_recent_activity'
        api_obj = self.get_api(api)
        res = await api_obj.get_user_recent_activity(user_id=user_id, limit=limit)

        self.log_request(request_name, api)
        return res

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
        self.mode_dict = {0: 'osu', 1: 'taiko', 2: 'fruits', 3: 'mania'}
        self.max_per_page = 50

    # users
    async def get_user(self, user, mode):
        mode_text = self.mode_to_text(mode)
        uri_base = 'users/{}/{}'.format(user, mode_text)
        uri_builder = URIBuilder(uri_base)
        uri = self.base.format(uri_builder.uri)
        res = await self.fetch(uri)
        return res

    async def get_user_recent(self, user,
                              include_fails=True, mode=0, limit=50, offset=0):

        mode_text = self.mode_to_text(mode)
        uri_base = 'users/{}/scores/recent?'.format(user)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('include_fails', include_fails)
        uri_builder.add_parameter('mode', mode_text)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.uri)

        res = await self.fetch(url)

        return res

    async def get_user_best(self, user, mode=0, limit=100, offset=0):
        mode_text = self.mode_to_text(mode)
        uri_base = 'users/{}/scores/best?'.format(user)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('mode', mode_text)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.uri)

        res = await self.fetch(url)

        return res

    async def get_user_firsts(self, user_id, mode=0, limit=50, offset=0):
        mode_text = self.mode_to_text(mode)
        uri_base = 'users/{}/scores/firsts?'.format(user_id)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('mode', mode_text)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.uri)

        res = await self.fetch(url)

        return res

    async def get_user_recent_activity(self, user_id, limit=50, offset=0):
        uri_base = 'users/{}/recent_activity?'.format(user_id)

        uri_builder = URIBuilder(uri_base)
        uri_builder.add_parameter('limit', limit)
        uri_builder.add_parameter('offset', offset)

        url = self.base.format(uri_builder.uri)

        res = await self.fetch(url)

        return res

    # request
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

    def mode_to_text(self, mode):
        return self.mode_dict[mode]
