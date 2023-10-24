import os
import asyncio
import requests


def send_group_message(data, users=None):
    asyncio.run(_send_group_message(data, users))


async def _send_group_message(data, users):
    url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/sendMessage'
    for u in users:
        data.update({"chat_id": u.telegram_id})
        task = asyncio.create_task(_send_message(data, url))


async def _send_message(data, url):
    res = requests.post(url=url, json=data)
    print(res.text)
