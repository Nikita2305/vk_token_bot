import os

import requests
import vk_api
from vk_api import VkUserPermissions

from vk_token_bot.utils import CaptchaApi


def download_captcha(link):
    path = "temp.png"
    with open(path, "wb") as f:
        response = requests.get(link)
        f.write(response.content)
    return path

import time
def obtain_code(path):
    api = CaptchaApi()
    res = api.method("in", {"method": "base64", "body": api.to_base(path)})
    status = res["status"]
    loc_id = res["request"]
    if (status != 1):
        return ""
    ITER = 10
    SLEEP = 3
    for i in range(ITER):
        res = api.method("res", {"action": "get", "id": loc_id})
        if (res["status"] == 1):
            return res["request"]
        loc_err = res["request"]
        time.sleep(SLEEP)
    return ""

def chandler(captcha):
    path = download_captcha(captcha.get_url())
    code = obtain_code(path)
    os.system("rm temp.png")
    return captcha.try_again(code)

def obtain_vk_token(vk_login, vk_password):
    vk_session = vk_api.VkApi(
        vk_login,
        vk_password,
        app_id=6121396,
        captcha_handler=chandler,
        scope=501202911,
    )
    vk_session.auth(token_only=True)
    print(vk_session.token['expires_in'])
    print(f'{vk_login}:{vk_session.token["access_token"]}')

def main():
    accounts = [
        # "79633158389:volUTHfRcdJiEg63",
        # "79196025007:W7AxVrwktbiPYkV2",
        # "79283844699:4uO8nM9SV8PICLTV",
        # "79122511310:WZLuLP0ZIAj7dsNF",
        # "79058369933:rF6f3Ujq88Xvx2bz",
        # "79162951700:y3sg4HTZwXAywYdx",
        # "79997235575:dHTkxTThRalUqhSr",
        # "79500310909:O0gAcpJyi4YmZxNv",
        # "79053427836:Ym3fwjJH7n25UEY3",
        # "201125298108:m01063356567",
        # "201026412306:Salma91!",
        # "201022658981:22nadaali97",
        # "201030091457:034209199",
    ]
    for account in accounts:
        obtain_vk_token(*account.split(':'))

if __name__ == '__main__':
    main()
