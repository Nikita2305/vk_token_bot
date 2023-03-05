from datetime import datetime
from vk_token_bot.utils import *
from vk_token_bot.access_manager import *
import traceback
import os

from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler
)

from telegram import (
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Document,
    ParseMode,
    ChatMember,
    Bot
)

class ErrorHandler (BasicCommunication):
    def __init__(self, *args, **kwargs):
        self.help_message = ""
        self.description = ""
        self.permissions = 0
        self.callbacks = []
        super().__init__(*args, **kwargs) 

    def execute(self, update, context):
        trace = ''.join(traceback.format_list(traceback.extract_tb(context.error.__traceback__)))
        logger.error(f"Update:\n{update}\n\nTrace:\n{trace}\nError: {context.error}") 
        try:
            context.bot.send_message(int(ADMIN_ID), "[Unhandled exception]")
        except Exception as ex:
            logger.debug(f"Error report was not sent to the admin, cause: {ex}")

class Start (BasicMessage):
        
    def __init__(self, *args, **kwargs):
        self.help_message = "start"
        self.description = ""
        self.permissions = USER | MANAGER
        super().__init__(*args, **kwargs)

    def execute(self, update, context):
        update.message.reply_text(f"Добрый день, {update.effective_user.full_name}. Этот бот даёт возможность создать токен Вконтакте и прикрепить его к прокси, если вам это необходимо. Токен необходим для совершения действий с аккаунта (например набор целевой аудитории или рассылка сообщений). Вам придётся ввести логин и пароль от Вконтакте, но мы их не сохраняем ни в каком виде, лишь генерируем токен и возвращаем в ответ. Перед тем, как воспользоваться этим ботом, рекомендуется посоветоваться с Кириллом или Никитой.\n\nЧтобы начать пользоваться, нажмите /get_vk_token.")
            
class Help (BasicMessage):
        
    def __init__(self, *args, **kwargs):
        self.help_message = "help"
        self.description = "Получить помощь"
        self.permissions = USER | MANAGER
        super().__init__(*args, **kwargs)

    def execute(self, update, context):
        update.message.reply_text(self.state.help_texts[self.state.access_manager_obj.get_status(
                                str(update.effective_user.id),
                                str(update.effective_user.username))
                            ],
        parse_mode=ParseMode.MARKDOWN)

class GetVkToken (BasicDialogue):
        
    def __init__(self, *args, **kwargs):
        self.help_message = "get_vk_token"
        self.description = "Получить vk-token"
        self.permissions = USER | MANAGER
        self.order = [
            SimpleHelloUnit("Введите токен доступа от администратора бота или нажмите /cancel, если он вам неизвестен.", entry_message=self.help_message),
            DialogueUnit(self.check_token)
        ]
        super().__init__(*args, **kwargs)

    def check_token(self, update, context):
        token = update.message.text
        try:
            self.state.token_handler.use_token(token)
        except Exception as ex:
            logger.debug(str(ex))
            update.message.reply_text("Токен не найден")
            return MessageActions.END
        update.message.reply_text("Токен успешно использован")
        return MessageActions.END
        

class AddToken (BasicMessage):
        
    def __init__(self, *args, **kwargs):
        self.help_message = "add_token"
        self.description = "Создать токен"
        self.permissions = MANAGER
        super().__init__(*args, **kwargs)

    def execute(self, update, context):
        token = self.state.token_handler.get_new_token()
        update.message.reply_text(token)

class GetTokens (BasicMessage):
        
    def __init__(self, *args, **kwargs):
        self.help_message = "get_tokens"
        self.description = "Получить список токенов"
        self.permissions = MANAGER
        super().__init__(*args, **kwargs)

    def execute(self, update, context):
        tokens = self.state.token_handler.get_tokens()
        update.message.reply_text("tokens:\n" + "\n".join(tokens))

class ProxyApiToken (BasicDialogue):
        
    def __init__(self, *args, **kwargs):
        self.help_message = "proxy_api_info"
        self.description = "Поменять proxy-api токен"
        self.permissions = MANAGER
        self.order = [
            SimpleHelloUnit("Введи новый токен или нажми /check (или /cancel).", entry_message=self.help_message),
            DialogueUnit(self.answer)
        ]
        super().__init__(*args, **kwargs)

    def answer(self, update, context):
        text = update.message.text.strip()
        if (text == "/check"):
            update.message.reply_text(f"proxy token: {self.state.proxy_api.get_token()}")
        else:
            self.state.proxy_api.set_token(text)
            update.message.reply_text("Установлен proxy-api токен: {text}")

class GetId (BasicMessage):
        
    def __init__(self, *args, **kwargs):
        self.help_message = "get_id"
        self.description = "Получить свой tg-id"
        self.permissions = USER | MANAGER
        super().__init__(*args, **kwargs)

    def execute(self, update, context):
        self.state.access_manager_obj.get_status(str(update.effective_user.id), str(update.effective_user.username))
        update.message.reply_text(str(update.effective_user.id))

class AddManager (BasicDialogue):

    def __init__(self, *args, **kwargs):
        self.help_message = "add_manager"
        self.description = "Добавить менеджера"
        self.permissions = MANAGER
        self.order = [
            SimpleHelloUnit("Введите его id, или /cancel, если не знаете",
                            entry_message=self.help_message),
            DialogueUnit(self.get_id)
        ]
        super().__init__(*args, **kwargs)

    def get_id(self, update, context):
        try:
            id = int(update.message.text)
        except Exception:
            update.message.reply_text("Введите число - id пользователя Telegram")
            return MessageActions.END
        self.state.access_manager_obj.set_status(update.message.text, MANAGER)
        update.message.reply_text("Добавлен " + update.message.text)
        return MessageActions.END

class EraseManager (BasicDialogue):

    def __init__(self, *args, **kwargs):
        self.help_message = "erase_manager"
        self.description = "Удалить менеджера"
        self.permissions = MANAGER
        self.order = [
            SimpleHelloUnit("Введите его id, или /cancel, если не знаете",
                            entry_message=self.help_message),
            DialogueUnit(self.get_id)
        ]
        super().__init__(*args, **kwargs)

    def get_id(self, update, context):
        try:
            id = int(update.message.text)
        except Exception as ex:
            update.message.reply_text("Необходимо число")
            return MessageActions.END
        self.state.access_manager_obj.set_status(update.message.text, USER)
        update.message.reply_text(f"Удалён {id}")
        return MessageActions.END

class GetManagers (BasicMessage):
        
    def __init__(self, *args, **kwargs):
        self.help_message = "get_managers"
        self.description = "Получить список менеджеров"
        self.permissions = MANAGER
        super().__init__(*args, **kwargs)

    def execute(self, update, context):
        ret = self.state.access_manager_obj.get_managers()
        s = "Вот они, сверху вниз:\n"
        for x in ret:
            s += "@" + x[1] + " (" + x[0] + ")\n"
        update.message.reply_text(s)
