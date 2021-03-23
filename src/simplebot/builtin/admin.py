from ..commands import command_decorator
from ..hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser) -> None:
    parser.add_subcommand(ban)
    parser.add_subcommand(unban)
    parser.add_subcommand(list_banned)
    parser.add_subcommand(AdminCmd)


class ban:
    """ban the given address."""

    def add_arguments(self, parser) -> None:
        parser.add_argument("addr", help="email address to ban")

    def run(self, bot, args, out) -> None:
        ban_addr(bot, args.addr)
        out.line("Banned: {}".format(args.addr))


class unban:
    """unban the given address."""

    def add_arguments(self, parser) -> None:
        parser.add_argument("addr", help="email address to unban")

    def run(self, bot, args, out) -> None:
        unban_addr(bot, args.addr)
        out.line("Unbanned: {}".format(args.addr))


class list_banned:
    """list banned addresses."""

    def run(self, bot, args, out) -> None:
        out.line(get_banned_list(bot))


class AdminCmd:
    """administrator tools."""

    name = "admin"
    db_key = "administrators"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "-a",
            "--add",
            help="grant administrator rights to an address.",
            metavar="ADDR",
        )
        parser.add_argument(
            "-d",
            "--del",
            help="revoke administrator rights to an address.",
            metavar="ADDR",
            dest="_del",
        )
        parser.add_argument(
            "-l", "--list", help="list administrators.", action="store_true"
        )

    def run(self, bot, args, out) -> None:
        if args.add:
            self._add(bot, args.add)
        elif args._del:
            self._del(bot, args._del)
        else:
            self._list(bot, out)

    def _add(self, bot, addr) -> None:
        add_admin(bot, addr)

    def _del(self, bot, addr) -> None:
        del_admin(bot, addr)

    def _list(self, bot, out) -> None:
        out.line(
            "Administrators:\n{}".format(bot.get(self.db_key, default="(Empty list)"))
        )


@command_decorator(name="/ban", admin=True)
def cmd_ban(command, replies) -> None:
    """Ban the given address or list banned addresses if no address is given.

    Examples:
    /ban foo@example.com
    /ban
    """
    if "@" in command.payload:
        ban_addr(command.bot, command.payload)
        replies.add(text="Banned: {}".format(command.payload))
    else:
        replies.add(text=get_banned_list(command.bot))


@command_decorator(name="/unban", admin=True)
def cmd_unban(command, replies) -> None:
    """Unban the given address.

    Examples:
    /unban foo@example.com
    """
    unban_addr(command.bot, command.payload)
    replies.add(text="Unbanned: {}".format(command.payload))


def ban_addr(bot, addr: str) -> None:
    contact = bot.get_contact(addr)
    contact.block()
    bot.plugins._pm.hook.deltabot_ban(bot=bot, contact=contact)


def unban_addr(bot, addr: str) -> None:
    contact = bot.get_contact(addr)
    contact.unblock()
    bot.plugins._pm.hook.deltabot_unban(bot=bot, contact=contact)


def get_banned_list(bot) -> str:
    addrs = []
    for contact in bot.account.get_blocked_contacts():
        addrs.append(contact.addr)
    return "Banned addresses:\n{}".format("\n".join(addrs) or "(Empty list)")


def get_admins(bot) -> list:
    return bot.get(AdminCmd.db_key, default="").split("\n")


def add_admin(bot, addr) -> None:
    existing = set()
    for a in bot.get(AdminCmd.db_key, default="").split("\n"):
        existing.add(a)
    assert "," not in addr
    existing.add(addr)
    bot.set(AdminCmd.db_key, "\n".join(existing))


def del_admin(bot, addr) -> None:
    existing = set()
    for a in bot.get(AdminCmd.db_key, default="").split("\n"):
        existing.add(a)
    existing.remove(addr)
    bot.set(AdminCmd.db_key, "\n".join(existing))


class TestCommandAdmin:
    def test_mock_cmd_ban(self, mocker):
        reply_msg = mocker.get_one_reply("/ban foo@example.com")
        assert reply_msg.text.lower().startswith("banned:")
        reply_msg = mocker.get_one_reply("/ban")
        assert not reply_msg.text.lower().startswith("banned:")

    def test_mock_cmd_unban(self, mocker):
        reply_msg = mocker.get_one_reply("/unban foo@example.com")
        assert reply_msg.text.lower().startswith("unbanned:")
