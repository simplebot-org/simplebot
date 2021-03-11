
from ..commands import command_decorator
from ..hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser):
    parser.add_subcommand(ban)
    parser.add_subcommand(unban)
    parser.add_subcommand(list_banned)
    parser.add_subcommand(AdminCmd)


class ban:
    """Ban the given address."""

    def add_arguments(self, parser):
        parser.add_argument("addr", help="email address to ban")

    def run(self, bot, args, out):
        ban_addr(bot, args.addr)
        out.line('Banned: {}'.format(args.addr))


class unban:
    """Unban the given address."""

    def add_arguments(self, parser):
        parser.add_argument("addr", help="email address to unban")

    def run(self, bot, args, out):
        unban_addr(bot, args.addr)
        out.line('Unbanned: {}'.format(args.addr))


class list_banned:
    """List banned addresses."""

    def add_arguments(self, parser):
        pass

    def run(self, bot, args, out):
        out.line(get_banned_list(bot))


class AdminCmd:
    """Administrator tools."""
    name = 'admin'
    db_key = 'administrators'

    def add_arguments(self, parser):
        parser.add_argument("addr", help="email address")
        parser.add_argument(
            "--add", help="grant administrator rights to an address.",
            metavar="ADDR")
        parser.add_argument(
            "--del", help="revoke administrator rights to an address.",
            metavar="ADDR", dest='_del')
        parser.add_argument(
            "--list", help="list administrators.",
            action='store_true')

    def run(self, bot, args, out):
        if args.add:
            self._add(bot, args.add)
        elif args._del:
            self._del(bot, args._del)
        else:
            self._list(bot, out)

    def _add(self, bot, addr):
        existing = list(x for x in bot.get(self.db_key, default="").split("\n") if x.strip())
        assert "," not in addr
        existing.append(addr)
        bot.set(self.db_key, "\n".join(existing))

    def _del(self, bot, addr):
        existing = list(x for x in bot.get(self.db_key, default="").split("\n") if x.strip())
        existing.remove(addr)
        bot.set(self.db_key, "\n".join(existing))

    def _list(self, bot, out):
        out.line('Administrators:\n{}'.format(
            bot.get(self.db_key, default='(Empty list)')))


@command_decorator(name='/ban', admin=True)
def cmd_ban(command, replies):
    """Ban the given address or list banned addresses if no address is given.

    Examples:
    /ban foo@example.com
    /ban
    """
    if '@' in command.payload:
        ban_addr(command.bot, command.payload)
        replies.add(text='Banned: {}'.format(command.payload))
    else:
        replies.add(text=get_banned_list(command.bot))


@command_decorator(name='/unban', admin=True)
def cmd_unban(command, replies):
    """Unban the given address.

    Examples:
    /unban foo@example.com
    """
    unban_addr(command.bot, command.payload)
    replies.add(text='Unbanned: {}'.format(command.payload))


def ban_addr(bot, addr: str) -> None:
    contact = bot.get_contact(addr)
    contact.block()
    bot.plugins._pm.hook.deltabot_ban(contact=contact)


def unban_addr(bot, addr: str) -> None:
    contact = bot.get_contact(addr)
    contact.unblock()
    bot.plugins._pm.hook.deltabot_unban(contact=contact)


def get_banned_list(bot) -> str:
    addrs = []
    for contact in bot.account.get_blocked_contacts():
        addrs.append(contact.addr)
    return 'Banned addresses:\n{}'.format('\n'.join(addrs) or '(Empty list)')


def get_admins(bot):
    return bot.get('administrators', default='').split('\n')


class TestCommandAdmin:
    def test_mock_cmd_ban(self, mocker):
        reply_msg = mocker.run_command("/ban foo@example.com")
        assert reply_msg.text.lower().startswith("banned:")
        reply_msg = mocker.run_command("/ban")
        assert not reply_msg.text.lower().startswith("banned:")

    def test_mock_cmd_unban(self, mocker):
        reply_msg = mocker.run_command("/unban foo@example.com")
        assert reply_msg.text.lower().startswith("unbanned:")
