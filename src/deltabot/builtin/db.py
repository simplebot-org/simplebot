
import os
import sqlite3
from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl(tryfirst=True)
def deltabot_init(bot):
    db_path = os.path.join(os.path.dirname(bot.account.db_path), "bot.db")
    bot.plugins.add_module("db", DBManager(db_path))


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._execute('''CREATE TABLE IF NOT EXISTS config
                        (keyname TEXT PRIMARY KEY,
                         value TEXT)''')

    def _execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    @deltabot_hookimpl
    def deltabot_store_setting(self, key, value):
        old_val = self.deltabot_get_setting(key)
        if value is not None:
            self._execute('REPLACE INTO config VALUES (?,?)', (key, value))
        else:
            self._execute('DELETE FROM config WHERE keyname=?', (key, ))
        return old_val

    @deltabot_hookimpl
    def deltabot_get_setting(self, key):
        row = self._execute(
            'SELECT * FROM config WHERE keyname=?',
            (key,),
        ).fetchone()
        return row['value'] if row else None

    @deltabot_hookimpl
    def deltabot_list_settings(self):
        rows = self._execute('SELECT * FROM config').fetchall()
        return [(row['keyname'], row["value"]) for row in rows]

    @deltabot_hookimpl
    def deltabot_shutdown(self, bot):
        self.db.close()


class TestDB:
    def test_settings_twice(self, mock_bot):
        mock_bot.set("hello", "world")
        assert mock_bot.get("hello") == "world"
        mock_bot.set("hello", "world")
        assert mock_bot.get("hello") == "world"

    def test_settings_scoped(self, mock_bot):
        mock_bot.set("hello", "world")
        mock_bot.set("hello", "xxx", scope="other")
        assert mock_bot.get("hello") == "world"
        assert mock_bot.get("hello", scope="other") == "xxx"

        l = mock_bot.list_settings()
        assert len(l) == 2
        assert l[0][0] == "global/hello"
        assert l[0][1] == "world"
        assert l[1][0] == "other/hello"
        assert l[1][1] == "xxx"
