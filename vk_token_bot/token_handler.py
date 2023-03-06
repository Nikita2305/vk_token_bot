import os
import random
import string
from vk_token_bot.utils import StateObject

CODE_LENGTH = 20

class TokenHandler (StateObject):
    path = os.path.dirname(__file__) + "/state/token_handler.txt" 
    def __init__(self):
        self.tokens = [] 
    def _gen_token(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=CODE_LENGTH))
    def get_new_token(self):
        token = self._gen_token()
        self.tokens += [token]
        return token
    def check_token(self, token):
        return token in self.tokens
    def use_token(self, token):
        if not self.check_token(token):
            raise RuntimeError("Token not found")
        self.tokens.pop(self.tokens.index(token))
    def get_tokens(self):
        return self.tokens

