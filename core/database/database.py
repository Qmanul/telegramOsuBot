import aiosqlite
from config_reader import config


class Database:
    def __init__(self):
        self.db_path = config.user_database_path.get_secret_value()

    async def db_start(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS profile"
                             "(telegram_user_id TEXT PRIMARY KEY NOT NULL,"
                             "username TEXT, user_id TEXT, gamemode TEXT)")
            await db.commit()

    async def update_user(self, user_id, update):
        async with aiosqlite.connect(self.db_path) as db:
            for key, item in update.items():
                await db.execute("UPDATE profile SET {} = '{}' WHERE user_id = '{}'".format(
                    key, item, user_id
                ))
            await db.commit()

    async def create_new_user(self, user, osu_user):
        new_user = {
            'telegram_user_id': user.id,
            'username': osu_user['username'],
            'user_id': str(osu_user['id']),
            'gamemode': 'osu'
        }
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT INTO profile(telegram_user_id, username, user_id, gamemode)"
                             "VALUES(:telegram_user_id, :username, :user_id, :gamemode)",
                             new_user)
            await db.commit()

    async def check_user_exists(self, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                    "SELECT * FROM profile WHERE telegram_user_id = '{user_id}'".format(user_id=user_id)) as cur:
                if await cur.fetchone() is None:
                    return False
                return True

    async def get_user(self, user_id):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM profile WHERE telegram_user_id = '{user_id}'".format(
                    user_id=user_id)) as cur:
                return await cur.fetchone()
