import os
from vk_token_bot.utils import StateObject

class ProxyApi (StateObject):
    path = os.path.dirname(__file__) + "/state/proxy_api.txt" 
    def __init__(self):
        self.token = "" 
    def get_token(self):
        return self.token
    def set_token(self, token):
        self.token = token

