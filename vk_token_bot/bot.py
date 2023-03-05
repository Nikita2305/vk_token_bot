from vk_token_bot.access_manager import *
from vk_token_bot.token_handler import *
from vk_token_bot.proxy_api import *
from vk_token_bot.functions import *
from vk_token_bot.utils import *
from functools import wraps

import os

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    ConversationHandler
)

def dump_system(state):
    logger.debug("Dumping system...") 
    state.dump()
    logger.debug("Successful!")

# deprecated menu_sender
def help_decorator(function, state):
    @wraps(function)
    def decorated(update, context):
        return function(update, context)
    return decorated

def cancel_decorator(function, state):
    @wraps(function)
    def decorated(update, context):
        message = obtain_message(update)
        if message is not None:    
            logger.debug(f"text: {message.text}\nuser: @{update.effective_user.username}")
            if (message.text == "/cancel"):
                logger.debug(f"~{function.__name__}() by cancel")
                return cancel(update, context)
        ret = function(update, context)
        dump_system(state)
        return ret
    return help_decorator(decorated, state)

def access_decorator(function, state):
    @wraps(function)
    def decorated(update, context):
        message = obtain_message(update) 
        if message is not None:
            logger.debug(f"text: {message.text}\nuser: @{update.effective_user.username}")
            user_permissions = state.access_manager_obj.get_status(str(update.effective_user.id), str(update.effective_user.username))
            if (not function in state.permissions[user_permissions]):
                logger.warning(f"Access denied for update: {update}")
                message.reply_text("Нет доступа к данной операции")
                logger.debug(f"~{function.__name__}() by cancel")
                return ConversationHandler.END
        ret = function(update, context)
        dump_system(state) 
        return ret
    return help_decorator(decorated, state)           

class State:
    
    def __init__(self, permissions, help_texts):
        self.permissions = permissions
        self.help_texts = help_texts
        self.should_save = []

    def add_object(self, key, obj, should_save=False):
        setattr(self, key, obj)
        if should_save:
            assert isinstance(obj, StateObject), f"{key} should be inherited from StateObject"
            self.should_save.append(obj)    

    def dump(self):
        for obj in self.should_save:
            obj.dump()

def main():
    # configuring globals
    help_texts = {USER: "", MANAGER: ""}
    permissions = {USER: [], MANAGER: []} 
    state = State(permissions, help_texts)

    # add some global object that will dump regularly
    access_manager = AccessManager.load_or_create() 
    access_manager.set_status(ADMIN_ID, MANAGER) 
    state.add_object("access_manager_obj", access_manager, should_save=True)

    token_handler = TokenHandler.load_or_create() 
    state.add_object("token_handler", token_handler, should_save=True)

    proxy_api = ProxyApi.load_or_create() 
    state.add_object("proxy_api", proxy_api, should_save=True)

    # setting up bot
    updater = Updater(BOT_KEY, use_context=True)
    dp = updater.dispatcher
    scenarios = [
        PermissionHelpText("\n*HELP:*\n", USER | MANAGER),

        Start(show_help=False),
        Help(show_help=False),
        GetId(show_help=False),
        GetVkToken(), 

        PermissionHelpText("\n*SETTINGS:*\n", MANAGER),  

        AddToken(),
        GetTokens(),

        ProxyApiToken(),

        PermissionHelpText("\n", MANAGER),

        EraseManager(),
        AddManager(), 
        GetManagers()
    ]

    # Static part:
    # Any function is wrapped with one of {access, cancel}_decorator to
    # automatically dump system
    # automatically send menu, when user cancels or finishes dialogue

    for new_obj in scenarios:
        logger.info(f"Adding handler: {new_obj}")
        if isinstance(new_obj, PermissionHelpText):
            for level in [USER, MANAGER]:
                if new_obj.permissions & level != 0:
                    state.help_texts[level] += new_obj.text
            continue
            
        new_obj.configure_globals(state)
        for level in [USER, MANAGER]:
            if level & new_obj.permissions != 0:
                if (new_obj.help_message is not None and new_obj.show_help):
                    command = new_obj.help_message.replace("_", "\_")
                    description = new_obj.description.replace("_", "\_")
                    state.help_texts[level] += f"/{command} - {description}\n"
                state.permissions[level] += [new_obj.get_callbacks()[0]]

        for i, callback in enumerate(new_obj.get_callbacks()):
            decorator = cancel_decorator
            if (i == 0):
                decorator = access_decorator
            new_obj.get_callbacks()[i] = decorator(callback, state)
       
        dp.add_handler(new_obj.convert_to_telegram_handler())

    error_handler = ErrorHandler()
    error_handler.configure_globals(state) 
    dp.add_error_handler(error_handler.execute)

    logger.debug("Polling was started")
    updater.start_polling()
    updater.idle()
    
if __name__ == '__main__':
    logger.warning("Bot is running now, logging enabled")
    main()
