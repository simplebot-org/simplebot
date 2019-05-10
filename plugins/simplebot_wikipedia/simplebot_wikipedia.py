# -*- coding: utf-8 -*-
from simplebot import Plugin
import wikipedia


class Wikipedia(Plugin):

    name = 'Wikipedia'
    description = 'Provides the !w <text> command to search <text> in Wikipedia. Ex. !w GNU.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!w <texto>` para buscar un artículo en la wikipedia. Ej. !w Cuba.'
            cls.PAGE_NOT_FOUND = 'Página no encontrada.'
        else:
            cls.PAGE_NOT_FOUND = 'Page not found.'
        wikipedia.set_lang(ctx.locale)
        
            

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!w', msg.text)
        if arg is not None:
            try:
                summary = wikipedia.summary(arg)
            except wikipedia.PageError:
                summary = cls.PAGE_NOT_FOUND
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(arg+':\n\n'+summary)
            return True
        return False
