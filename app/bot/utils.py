import os
import copy
import asyncio
import requests


def send_group_message(data, users=None, message_type="TXT"):
    asyncio.run(_send_group_message(data, users, message_type=message_type))


async def _send_group_message(data, users, message_type="TXT"):
    SEND_TYPE = {
        "TXT": "sendMessage",
        "PHO": "sendPhoto",
    }
    send_method = SEND_TYPE.get(message_type, None)
    if not send_method:
        return False
    url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_BOT_TOKEN")}/{send_method}'
    for u in users:
        data.update({"chat_id": u.telegram_id})
        task = asyncio.create_task(_send_message(copy.deepcopy(data), url))
    return True


async def _send_message(data, url):
    res = requests.post(url=url, json=data)
