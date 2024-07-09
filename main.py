import requests
import vk_api

def main():
    session = requests.Session()
    vk_session = vk_api.VkApi(
        "+79507990996",
        "C020903c!",
        app_id=6287487,
        session=session,
    )
    vk_session.auth(token_only=True)
    print(vk_session.token["access_token"])


if __name__ == '__main__':
    main()