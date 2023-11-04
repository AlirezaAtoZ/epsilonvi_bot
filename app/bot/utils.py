import logging
import os
import copy
import asyncio
import requests

from django.conf import settings


def send_group_message(data, users=None, message_type="TXT"):
    logger = logging.getLogger(__name__)
    logger.error(f"sending message to: {users=}")
    asyncio.run(_send_group_message(data, users, message_type=message_type))


async def _send_group_message(data, users, message_type="TXT"):
    SEND_TYPE = {
        "TXT": "sendMessage",
        "PHO": "sendPhoto",
    }
    send_method = SEND_TYPE.get(message_type, None)
    if not send_method:
        return False
    url = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{send_method}'
    for u in users:
        data.update({"chat_id": u.telegram_id})
        task = asyncio.create_task(_send_message(copy.deepcopy(data), url))
    return True


async def _send_message(data, url):
    res = requests.post(url=url, json=data)
