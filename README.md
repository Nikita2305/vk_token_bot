# vk_token_bot

## To prepare
./scripts/setup.sh

And also add file `vk_token_bot/vk_token_bot/credentials.json` with the following structure:
```json
{
"admin_id": "ADMIN_TG_ID",
"bot_token": "TG_BOT_TOKEN",
"captcha_token": "CAPTCHA_TOKEN"
}
```

Also you can add this line (optional):
```json
"user_agent": "EXPLICIT_USER_AGENT"
```

## To run the bot
./scripts/start.sh
