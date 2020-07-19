
import pytest


def hitchhiker(message, replies):
    """ my incoming message filter example. """
    if "42" in message.text:
        replies.add(text="correct answer!")
    else:
        replies.add(text="try again!")


def test_register(mock_bot):
    mock_bot.filters.register(name="hitchhiker", func=hitchhiker)
    with pytest.raises(ValueError):
        mock_bot.filters.register(name="hitchhiker", func=hitchhiker)

    mock_bot.filters.unregister("hitchhiker")
    assert "hitchhiker" not in mock_bot.filters.dict()


def test_simple_filter(bot_tester):
    bot_tester.bot.filters.register(name="hitchhiker", func=hitchhiker)
    msg_reply = bot_tester.send_command("hello 42")
    assert msg_reply.text == "correct answer!"
    msg_reply = bot_tester.send_command("hello 10")
    assert msg_reply.text == "try again!"


def test_pseudo_downloader(bot_tester):
    def downloader(message, replies):
        """ pseudo downloader of https"""
        if "https" in message.text:
            replies.add(text="downloaded", filename=__file__)

    bot_tester.bot.filters.register(name="downloader", func=downloader)
    msg_reply = bot_tester.send_command("this https://qwjkeqwe")
    assert msg_reply.text == "downloaded"
    assert msg_reply.filename != __file__  # blobdir
    with open(msg_reply.filename) as f:
        content = f.read()
    assert content == open(__file__).read()
