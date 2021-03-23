import os
import sqlite3

from ..hookspec import deltabot_hookimpl


@deltabot_hookimpl(tryfirst=True)
def deltabot_init(bot) -> None:
    db_path = os.path.join(os.path.dirname(bot.account.db_path), "bot.db")
    bot.plugins.add_module("db", DBManager(db_path))


class DBManager:
    def __init__(self, db_path: str) -> None:
        self.db = sqlite3.connect(
            db_path, check_same_thread=False, isolation_level=None
        )
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS config"
                " (keyname TEXT PRIMARY KEY,value TEXT)"
            )
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS msgs" " (id INTEGER PRIMARY KEY)"
            )

    def put_msg(self, msg_id: int) -> None:
        with self.db:
            self.db.execute("INSERT INTO msgs VALUES (?)", (msg_id,))

    def pop_msg(self, msg_id: int) -> None:
        with self.db:
            self.db.execute("DELETE FROM msgs WHERE id=?", (msg_id,))

    def get_msgs(self) -> list:
        return [r[0] for r in self.db.execute("SELECT * FROM msgs").fetchall()]

    @deltabot_hookimpl
    def deltabot_store_setting(self, key: str, value: str) -> None:
        with self.db:
            if value is not None:
                self.db.execute("REPLACE INTO config VALUES (?,?)", (key, value))
            else:
                self.db.execute("DELETE FROM config WHERE keyname=?", (key,))

    @deltabot_hookimpl
    def deltabot_get_setting(self, key: str) -> None:
        row = self.db.execute("SELECT * FROM config WHERE keyname=?", (key,)).fetchone()
        return row and row["value"]

    @deltabot_hookimpl
    def deltabot_list_settings(self) -> list:
        rows = self.db.execute("SELECT * FROM config").fetchall()
        return [(row["keyname"], row["value"]) for row in rows]

    @deltabot_hookimpl
    def deltabot_shutdown(self, bot) -> None:
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
