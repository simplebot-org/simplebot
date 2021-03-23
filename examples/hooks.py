"""
This example illustrates how to use some of simplebot's hooks at the
package level and also in a class that is registered as a plugin.
To see all available hooks check ``simplebot.hookspec``
"""

import simplebot


@simplebot.hookimpl
def deltabot_init(bot):
    bot.plugins.add_module("grouplogging", GroupLoggingPlugin())


class GroupLoggingPlugin:
    @simplebot.hookimpl
    def deltabot_incoming_message(self, message):
        message.chat.send_text(
            "bot: incoming_message sys={} body={!r}".format(
                message.is_system_message(), message.text
            )
        )

    @simplebot.hookimpl
    def deltabot_member_added(self, chat, contact, actor, message, replies):
        replies.add("bot: member_added {}".format(contact.addr))

    @simplebot.hookimpl
    def deltabot_member_removed(self, chat, contact, actor, message, replies):
        replies.add("bot: member_removed {}".format(contact.addr))


class TestGroupLoggingPlugin:
    def test_events(self, bot_tester, acfactory, lp):
        lp.sec("creating test accounts")
        ac3 = acfactory.get_one_online_account()

        lp.sec("create a group chat with only bot and the sender account")
        chat = bot_tester.send_account.create_group_chat("test")
        chat.add_contact(bot_tester.bot_contact)

        lp.sec("send a text and wait for reply")
        chat.send_text("some")
        reply = bot_tester.get_next_incoming()
        assert "some" in reply.text
        assert "sys=False" in reply.text

        lp.sec("add ac3 account to group chat")
        chat.add_contact(ac3)
        reply = bot_tester.get_next_incoming()
        assert "member_added" in reply.text
        assert ac3.get_config("addr") in reply.text

        lp.sec("remove ac3 account from group chat")
        chat.remove_contact(ac3)
        reply = bot_tester.get_next_incoming()
        assert "member_removed" in reply.text
        assert ac3.get_config("addr") in reply.text
