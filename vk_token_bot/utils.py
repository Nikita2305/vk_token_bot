import os 
credentials_path = os.path.dirname(__file__) + "/credentials.json"
DATABASE_ENC_KEY = "vk_parse_bot_1234"

import json
with open(credentials_path, "r") as f:
    creds = json.load(f)    
    ADMIN_ID = creds["admin_id"]
    BOT_KEY = creds["bot_token"]

from vk_token_bot.logging_config import *
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(toplevel)

import jsonpickle
class StateObject:
    def __init__(self):
        pass

    @classmethod
    def load_or_create(cls, *args, **kwargs):
        if not hasattr(cls, "path"):
            raise RuntimeError(f"Need to define path as static member of class {cls.__name__}")
        try:
            with open(cls.path) as f:
                ret = jsonpickle.decode(f.read())
                logger.debug(f"Loaded {cls.__name__} from file")
                return ret
        except Exception as ex:
            logger.debug(f"Error {ex} while")
            return cls(*args, **kwargs)
        
    def dump(self):
        with open(self.path, 'w') as f:
            print(jsonpickle.encode(self, indent=4), file=f)

from enum import Enum
MessageActions = Enum('MessageActions', ['NEXT', 'PREV', 'REDO', 'END'])

from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters, 
    ConversationHandler
)

from telegram import (
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Document,
    ParseMode
)

def cancel(update, context):
    update.message.reply_text("Отменил текущее действие")
    return ConversationHandler.END

def obtain_message(update, delete=False):
    if (delete):
        logger.debug(f"Obtaining message from {update}")
    try:
        message = update.message
        if (message == None):
            raise Exception("Raised error")
        if (delete):
            logger.debug(f"Got as forward message")
    except Exception as ex:
        if (delete):
            logger.debug(f"Expecting raised error: {ex}")
        try:
            message = update.callback_query.message
        except Exception as ex:
            logger.debug("Not a message probably")
            return None
        if (delete):
            logger.debug(f"Got as callback message")
        if (delete):
            logger.debug("Trying to delete menu")
            try:
                message.delete() # deleting menu
                logger.debug("Deleted successfully")
            except Exception as ex1:
                logger.warning(f"Menu from update cannot be deleted\nUpdate: {update}\nCause: {ex1}")
    return message

class BasicCommunication:
    
    def __init__(self, show_help=True):
        if (not hasattr(self, "callbacks") or
            not hasattr(self, "help_message") or
            not hasattr(self, "permissions") or 
            not hasattr(self, "description")):
            raise RuntimeError("Expected Communication parameters")
        self.show_help = show_help
    
    def configure_globals(self, state):
        self.state = state

    # Changable array
    def get_callbacks(self):
        return self.callbacks

    def convert_to_telegram_handler(self):
        return NotImplementedError("abstract class!")

class PermissionHelpText:
    
    def __init__(self, text, permissions):
            self.text = text
            self.permissions = permissions

class BasicMessage (BasicCommunication):
    
    def __init__(self, handler=None, *args, **kwargs):
        self.handler = (handler if handler is not None else CommandHandler(self.help_message, None))
        self.callbacks = [self.execute]
        super().__init__(*args, **kwargs) 

    def execute(self, update, context):
        return NotImplementedError("abstract class!")

    def update_callbacks(self):
        self.execute = self.callbacks[0]

    def convert_to_telegram_handler(self):
        self.update_callbacks()
        self.handler.callback = self.execute
        return self.handler

class BasicDialogue (BasicCommunication):

    def __init__(self, *args, **kwargs):
        if (not hasattr(self, "order")):
            raise RuntimeError("Expected Dialogue parameters") 
        self.init_order()
        self.callbacks = [unit.cute_handle for unit in self.order]
        super().__init__(*args, **kwargs)

    def init_order(self):
        for i, unit in enumerate(self.order):
            unit.order_id = i

    def update_callbacks(self):
        if len(self.order) != len(self.callbacks):
            raise RuntimeError("Unexpected state")
        for i, unit in enumerate(self.order):
            for handler in unit.handlers:
                handler.callback = self.callbacks[i]

    def convert_to_telegram_handler(self):
        self.update_callbacks()
        states = dict()
        for i in range(1, len(self.order)):
            states[i] = self.order[i].handlers
        return ConversationHandler(
            entry_points=self.order[0].handlers,
            states=states,
            fallbacks=[MessageHandler(Filters.all, cancel)]
        )

class DialogueUnit:

    def __init__(self, callback, order_id=None, entry_message=None, other_handlers=[]):
        self.callback = callback
        if entry_message is not None:
            self.handlers = other_handlers + [CommandHandler(entry_message, self.cute_handle)]
        elif len(other_handlers) == 0:
            self.handlers = [MessageHandler(Filters.text, self.cute_handle)]
        else:
            self.handlers = other_handlers

        for handler in self.handlers:
            handler.callback = self.cute_handle

        self.order_id = order_id

    def cute_handle(self, update, context):
        ret = self.callback(update, context)
        match ret:
            case MessageActions.NEXT:
                return self.order_id + 1
            case MessageActions.PREV:
                return self.order_id - 1
            case MessageActions.REDO:
                return self.order_id
            case MessageActions.END:
                return ConversationHandler.END
        return ret

class SimpleHelloUnit (DialogueUnit):

    def __init__(self, message, *args, **kwargs):
        if (len(message) == 0):
            raise RuntimeError("Expected non-empty string")
        self.message = message
        super().__init__(self.handle, *args, **kwargs)

    def handle(self, update, context):
        message = obtain_message(update)
        message.reply_text(self.message)
        return MessageActions.NEXT

class ReadWriteUnit (DialogueUnit):

    def __init__(self, context_key, message, *args, **kwargs):
        if (len(message) == 0 or len(context_key) == 0):
            raise RuntimeError("Expected non-empty strings")
        self.context_key = context_key
        self.message = message
        super().__init__(self.handle, *args, **kwargs)

    def handle(self, update, context):
        message = obtain_message(update)
        context[self.context_key] = message.text
        message.reply_text(self.message)
        return MessageActions.NEXT
