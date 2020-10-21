
from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser):
    parser.add_subcommand(ban)
    parser.add_subcommand(unban)
    parser.add_subcommand(list_banned)
    parser.add_subcommand(add_admin)
    parser.add_subcommand(del_admin)
    parser.add_subcommand(list_admin)


@deltabot_hookimpl
def deltabot_init(bot):
    bot.commands.register(name="/ban", func=cmd_ban, admin=True)
    bot.commands.register(name="/unban", func=cmd_unban, admin=True)


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


class add_admin:
    """Grant administrator rights to an address."""

    db_key = "administrators"

    def add_arguments(self, parser):
        parser.add_argument("addr", help="email address")

    def run(self, bot, args, out):
        existing = list(x for x in bot.get(self.db_key, default="").split("\n") if x.strip())
        assert "," not in args.addr
        existing.append(args.addr)
        bot.set(self.db_key, "\n".join(existing))


class del_admin(add_admin):
    """Revoke administrator rights to an address."""

    def run(self, bot, args, out):
        existing = list(x for x in bot.get(self.db_key, default="").split("\n") if x.strip())
        existing.remove(args.addr)
        bot.set(self.db_key, "\n".join(existing))


class list_admin:
    """List addresses with administrator rights."""

    db_key = "administrators"

    def add_arguments(self, parser):
        pass

    def run(self, bot, args, out):
        out.line('Administrators:\n{}'.format(
            bot.get(self.db_key, default='(Empty list)')))


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
