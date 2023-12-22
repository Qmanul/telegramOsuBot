from core.osu.osuAPI import OsuApi
from config_reader import config

o = OsuApi(config.client_id.get_secret_value(), config.client_secret.get_secret_value())

t = o.get_user_recent_activity(11232191)

print(t)
