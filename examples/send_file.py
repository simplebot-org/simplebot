"""
This example illustrates how to reply with a file.
This plugin uses a 3rd party lib so you will need to install it first:

    $ pip install xkcd
"""

import io
from urllib.request import urlopen

import xkcd

import simplebot


@simplebot.command(name="/xkcd")
def cmd_xkcd(replies):
    """Send ramdom XKCD comic."""
    comic = xkcd.getRandomComic()
    image = io.BytesIO(urlopen(comic.imageLink).read())
    text = "#{} - {}\n\n{}".format(comic.number, comic.title, comic.altText)
    # we could omit bytefile and only send filename with a path to a file
    replies.add(text=text, filename=comic.imageName, bytefile=image)


class TestSendFile:
    def test_cmd_xkcd(self, mocker):
        msg = mocker.get_one_reply("/xkcd")
        assert msg.text.startswith("#")
        assert msg.filename
        assert msg.is_image()
