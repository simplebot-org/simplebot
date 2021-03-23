import pytest


def test_general_help(cmd):
    cmd.run_ok(
        [],
        """
        *show-ffi*
        *init*
        *info*
        *serve*
    """,
    )


def test_version(cmd):
    from simplebot import __version__ as version

    cmd.run_ok(
        ["--version"],
        """
        *{}*
    """.format(
            version
        ),
    )


class TestSettings:
    def test_get_set_list(self, mycmd, session_liveconfig):
        mycmd.run_fail(["db", "--get", "hello"])
        mycmd.run_fail(["db", "--set", "hello", "world"])
        mycmd.run_ok(["db", "--set", "global/hello", "world"])
        mycmd.run_ok(
            ["db", "--get", "global/hello"],
            """
            world
        """,
        )
        mycmd.run_ok(
            ["db", "--list"],
            """
            global/hello: world
        """,
        )
        mycmd.run_ok(
            ["db", "--del", "global/hello"],
            """
            *delete*
        """,
        )
        out = mycmd.run_ok(["db", "--list"])
        assert "hello" not in out


class TestInit:
    def test_ok_then_info(self, mycmd, session_liveconfig):
        if not session_liveconfig:
            pytest.skip("no temporary accounts")
        config = session_liveconfig.get(0)
        mycmd.run_ok(
            ["--stdlog=info", "init", config["addr"], config["mail_pw"]],
            """
            *deltabot*INFO*Success*
        """,
        )
        mycmd.run_ok(
            ["info"],
            """
            *database_version*
        """,
        )

    def test_fail_then_ok(self, mycmd, session_liveconfig):
        if not session_liveconfig:
            pytest.skip("no temporary accounts")
        config = session_liveconfig.get(0)
        mycmd.run_fail(
            ["--stdlog", "info", "init", config["addr"], "Wrongpw"],
            """
            *deltabot*ERR*
        """,
        )
        mycmd.run_ok(
            ["--std=info", "init", config["addr"], config["mail_pw"]],
            """
            *deltabot*INFO*Success*
        """,
        )

    def test_serve(self, mycmd, session_liveconfig, monkeypatch):
        import deltachat

        if not session_liveconfig:
            pytest.skip("no temporary accounts")
        config = session_liveconfig.get(0)
        mycmd.run_ok(["--std=info", "init", config["addr"], config["mail_pw"]], "")
        monkeypatch.setattr(deltachat.account.Account, "wait_shutdown", lambda x: 0 / 0)
        with pytest.raises(ZeroDivisionError):
            mycmd.run_ok(["--show-ffi", "serve"], "")


class TestPluginManagement:
    def test_list_plugins(self, mycmd):
        mycmd.run_ok(
            ["plugin", "--list"],
            """
            *simplebot.builtin.*
        """,
        )

    def test_add_del_list_module(self, mycmd, examples):
        filename = "quote_reply.py"
        path = examples.join(filename).strpath
        mycmd.run_ok(["plugin", "--add", path], "*{}*".format(path))
        mycmd.run_ok(
            ["plugin", "--list"],
            """
            *{}*
        """.format(
                filename
            ),
        )
        mycmd.run_ok(
            ["plugin", "--del", path],
            """
            *removed*1*
        """,
        )
        out = mycmd.run_ok(["plugin", "--list"])
        assert filename not in out
