"""
This example illustrates how to use objects from deltachat API.
For more info check deltachat package's documentation.
"""

import simplebot


@simplebot.filter
def message_info(message, replies):
    """Send info about the received message."""
    lines = []

    sender = message.get_sender_contact()
    lines.append("Contact:")
    lines.append("Name: {}".format(sender.name))
    lines.append("Address: {}".format(sender.addr))
    lines.append("Verified: {}".format(sender.is_verified()))
    lines.append("Status: {!r}".format(sender.status))

    lines.append("")

    lines.append("Message:")
    lines.append("Encrypted: {}".format(message.is_encrypted()))
    if message.is_text():
        t = "text"
    elif message.is_image():
        t = "image"
    elif message.is_gif():
        t = "gif"
    elif message.is_audio():
        t = "audio"
    elif message.is_video():
        t = "video"
    elif message.is_file():
        t = "file"
    else:
        t = "unknown"
    lines.append("Type: {}".format(t))
    if message.filename:
        lines.append("Attachment: {}".formmat(message.filename))

    lines.append("")

    chat = message.chat
    lines.append("Chat:")
    lines.append("Name: {}".format(chat.get_name()))
    lines.append("ID: {}".format(chat.id))
    lines.append("Type: {}".format("group" if chat.is_group() else "private"))
    if chat.is_group():
        lines.append("Member Count: {}".format(len(chat.get_contacts())))

    replies.add(text="\n".join(lines))


class TestDeltaChatApi:
    def test_message_info(self, mocker):
        addr = "addr@example.org"
        msg = mocker.get_one_reply(text="deltachat_api", addr=addr, filters=__name__)
        assert addr in msg.text
