import os
import requests
import random
from vk_token_bot.utils import StateObject, logger, USER_AGENTS

class ProxyApiHttpError(Exception):

    def __init__(self, method, values, response):
        super().__init__()
        self.method = method
        self.values = values
        self.response = response

    def __str__(self):
        return 'Http error, response code {}'.format(self.response.status_code)

class ProxyApi (StateObject):
    path = os.path.dirname(__file__) + "/state/proxy_api.txt" 
    TOTAL_PROXIES = 500
    PAGE_SIZE = 100
    MAX_PROXY_USAGES = 3

    def __init__(self):
        self.token = "" 
        self.proxies = list()
    
    def get_token(self):
        return self.token
    
    def set_token(self, token):
        self.token = token
    
    def config2text(self, cfg):
        return "http://{}:{}@{}:{}".format(cfg["username"], cfg["password"], cfg["proxy_address"], cfg["port"])
 
    def assign_proxy(self):
        self.update_proxies()
        for i in range(len(self.proxies)):
            if self.proxies[i]["valid"] and self.proxies[i]["used"] < ProxyApi.MAX_PROXY_USAGES:
                self.proxies[i]["used"] += 1
                user_agent = random.choice(USER_AGENTS) 
                return self.proxies[i], user_agent
        error_message = "No more proxies in bot"
        logger.error(error_message)
        raise RuntimeError(error_message)

    def update_proxies(self):
        used = dict()
        for proxy in self.proxies:
            used[proxy["proxy_address"]] = proxy["used"]
        old_proxies = self.proxies
        self.proxies = self.get_proxies_from_api()
        for proxy in self.proxies:
            if proxy["proxy_address"] not in used:
                proxy["used"] = 0
            else:
                proxy["used"] = used[proxy["proxy_address"]]

    def get_proxies_from_api(self):        
        proxy_list = []
        pages_count = int(ProxyApi.TOTAL_PROXIES // ProxyApi.PAGE_SIZE)
        pages_count += int(ProxyApi.TOTAL_PROXIES % ProxyApi.PAGE_SIZE != 0)
        for i in range(pages_count):
            proxy_list += self.method("proxy/list/",
                                    {
                                        "mode": "direct",
                                        "ordering": "proxy_address",
                                        "page_size": ProxyApi.PAGE_SIZE,
                                        "page": i + 1
                                    }
            )["results"]
        return proxy_list
        
    def method(self, method, params={}):
        """ Вызов метода API
        :param method: Название метода. proxy/list в качестве примера
        :type method: str
        
        :param params: Параметры
        :type params: dict
        Бросает `ProxyApiHttpError` в случае неуспешного кода возварата http запроса
        
        Возвращает `response`.
        """
        params = params.copy() if params else {}

        response = requests.get(
            f"https://proxy.webshare.io/api/v2/{method}",
            params=params,
            headers={"Authorization": self.token}
        )
        if response.ok:
            try:
                response = response.json()
            except Exception as ex:
                raise RuntimeError(f"Error while convering to json: {ex}")
        else:
            raise ProxyApiHttpError(method, params, response)
        
        return response
