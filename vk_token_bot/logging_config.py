import logging.config
import os
from vk_token_bot.utils import ADMIN_ID, BOT_KEY
from telegram import Bot

toplevel = 'vk_token_bot'

class TelegramBotHandler(logging.Handler):
    def __init__(self):
        super().__init__()

    def emit(self, record: logging.LogRecord):
        try:
            Bot(BOT_KEY).send_message(int(ADMIN_ID), str(self.format(record)))
        except Exception as ex:
            logging.getLogger(toplevel).info("Previous report was not sent by Telegram")

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'default_formatter': {
            'format': '[%(levelname)s:%(asctime)s] %(message)s'
        },
    },

    'handlers': {
        'stream_handler': {
            'class': 'logging.FileHandler',
            'filename': os.path.dirname(__file__) + '/logs.txt',
            'level': 'DEBUG',
            'formatter': 'default_formatter'
        },
        'telegram_handler': {
            'class': 'vk_token_bot.logging_config.TelegramBotHandler',
            'level': 'WARNING',
            'formatter': 'default_formatter'
        }
    },

    'loggers': {
        toplevel: {
            'handlers': ['stream_handler', 'telegram_handler'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}
