import json
import os
from vk_token_bot.utils import StateObject

USER = 1
MANAGER = 2

class AccessManager (StateObject):
    path = os.path.dirname(__file__) + "/state/access_manager.txt" 
    def __init__(self):
        self.keys = dict() 
    def set_status(self, id: str, status: int):
        if id in self.keys:
            self.keys[id] = (status, self.keys[id][1])
        else:
            self.keys[id] = (status, "None")
    def set_nickname(self, id: str, nickname: str):
        if id in self.keys:
            self.keys[id] = (self.keys[id][0], nickname)
        else:
            self.keys[id] = (USER, nickname)
    def get_status(self, id: str, nickname: str):
        self.set_nickname(id, nickname)    
        return self.keys[id][0]
    def get_managers(self):
        return [(key, self.keys[key][1]) for key in self.keys if self.keys[key][0] == MANAGER]
