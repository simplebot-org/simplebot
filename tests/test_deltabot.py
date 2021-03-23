import io

import pytest

from simplebot.bot import Replies


class TestDeltaBot:
    def test_self_contact(self, mock_bot):
        contact = mock_bot.self_contact
        assert contact.addr
        assert contact.display_name
        assert contact.id

    def test_get_contact(self, mock_bot):
        contact = mock_bot.get_contact("x@example.org")
        assert contact.addr == "x@example.org"
        assert contact.display_name == "x@example.org"

        contact2 = mock_bot.get_contact(contact)
        assert contact2 == contact

        contact3 = mock_bot.get_contact(contact.id)
        assert contact3 == contact

    def test_get_chat(self, mock_bot):
        chat = mock_bot.get_chat("x@example.org")
        contact = mock_bot.get_contact("x@example.org")
        assert contact.get_chat() == chat
        assert mock_bot.get_chat(contact) == chat
        assert mock_bot.get_chat(chat.id) == chat

        msg = chat.send_text("hello")
        assert mock_bot.get_chat(msg) == chat

    def test_create_group(self, mock_bot):
        members = set(["x{}@example.org".format(i) for i in range(3)])
        chat = mock_bot.create_group("test", contacts=members)
        assert chat.get_name() == "test"
        assert chat.is_group()
        for contact in chat.get_contacts():
            members.discard(contact.addr)
        assert not members


class TestSettings:
    def test_set_get_list(self, mock_bot):
        mock_bot.set("a", "1")
        mock_bot.set("b", "2")
        l = mock_bot.list_settings()
        assert len(l) == 2
        assert l == [("global/a", "1"), ("global/b", "2")]


class TestReplies:
    @pytest.fixture
    def replies(self, mock_bot, mocker):
        incoming_message = mocker.make_incoming_message("0")
        return Replies(incoming_message, mock_bot.logger)

    def test_two_text(self, replies):
        replies.add(text="hello")
        replies.add(text="world")
        l = replies.send_reply_messages()
        assert len(l) == 2
        assert l[0].text == "hello"
        assert l[1].text == "world"

    def test_filename(self, replies, tmpdir):
        p = tmpdir.join("textfile")
        p.write("content")
        replies.add(text="hello", filename=p.strpath)
        l = replies.send_reply_messages()
        assert len(l) == 1
        assert l[0].text == "hello"
        s = open(l[0].filename).read()
        assert s == "content"

    def test_file_content(self, replies):
        bytefile = io.BytesIO(b"bytecontent")
        replies.add(text="hello", filename="something.txt", bytefile=bytefile)

        l = replies.send_reply_messages()
        assert len(l) == 1
        assert l[0].text == "hello"
        assert l[0].filename.endswith(".txt")
        assert "something" in l[0].filename
        s = open(l[0].filename, "rb").read()
        assert s == b"bytecontent"

    def test_chat_incoming_default(self, replies):
        replies.add(text="hello")
        l = replies.send_reply_messages()
        assert len(l) == 1
        assert l[0].text == "hello"
        assert l[0].chat == replies.incoming_message.chat

    def test_different_chat(self, replies, mock_bot):
        chat = mock_bot.account.create_group_chat("new group")
        replies.add(text="this", chat=chat)
        l = replies.send_reply_messages()
        assert len(l) == 1
        assert l[0].text == "this"
        assert l[0].chat.id == chat.id
