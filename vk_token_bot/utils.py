import os 
credentials_path = os.path.dirname(__file__) + "/credentials.json"

import json
with open(credentials_path, "r") as f:
    creds = json.load(f)    
    ADMIN_ID = creds["admin_id"]
    BOT_KEY = creds["bot_token"]
    CAPTCHA_TOKEN = creds["captcha_token"]
    EXPLICIT_USER_AGENT = ""
    if "user_agent" in creds:
        EXPLICIT_USER_AGENT = creds["user_agent"]

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

import requests
import base64
class CaptchaApi:

    def __init__(self, token=CAPTCHA_TOKEN):
        self.token = token

    def to_base(self, filename):
        with open(filename, "rb") as image2string:
            converted_string = base64.b64encode(image2string.read())
        return converted_string

    def method(self, method, params={}):
        params = params.copy() if params else {}

        params["key"] = self.token
        params["json"] = 1

        response = requests.get(
            f"http://rucaptcha.com/{method}.php",
            params=params
        )

        if response.ok:
            response = response.json()
        else:
            raise RuntimeError(f"something went wrong: {response.status_code}")

        return response

def download_captcha(link):
    path = "temp.png"
    with open(path, "wb") as f:
        response = requests.get(link)
        f.write(response.content)
    return path

def obtain_code(path):
    api = CaptchaApi()
    res = api.method("in", {"method": "base64", "body": api.to_base(path)})
    status = res["status"]
    loc_id = res["request"]
    if (status != 1):
        logger.error(f"Captcha api error: {loc_id}")
        return ""
    ITER = 10
    SLEEP = 3
    for i in range(ITER):
        res = api.method("res", {"action": "get", "id": loc_id})
        if (res["status"] == 1):
            return res["request"]
        loc_err = res["request"]
        logger.debug(f"Captcha small error: {loc_err}")
        time.sleep(SLEEP)
    logger.error("Didnt get captcha after 10 iterations")
    return ""

def chandler(captcha):
    path = download_captcha(captcha.get_url())
    logger.debug(f"chandler path {path}")
    code = obtain_code(path)
    logger.debug(f"chandler code {code}")
    os.system("rm temp.png")
    return captcha.try_again(code)

import vk_api
def obtain_vk_token(session, vk_login, vk_password):
    vk_session = vk_api.VkApi(
        vk_login,
        vk_password,
        captcha_handler=chandler,
        app_id=2685278,
        session=session
    )  
    vk_session.auth(token_only=True)
    os.system("rm vk_config.v2.json")
    return vk_session.token["access_token"]

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
        context.user_data[self.context_key] = message.text
        message.reply_text(self.message)
        return MessageActions.NEXT

USER_AGENTS = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36', 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.71 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.83 Safari/537.1', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36', 'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36', 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.143 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36', 'Mozilla/5.0 (X11; OpenBSD i386) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.64 Safari/537.31', 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36', 'Mozilla/5.0 (Linux; Android 6.0; LG-H631 Build/MRA58K) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/38.0.2125.102 Mobile Safari/537.36', 'Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36']


