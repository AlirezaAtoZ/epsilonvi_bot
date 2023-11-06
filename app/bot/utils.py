import logging
import os
import copy
import asyncio
import requests

from django.conf import settings


def send_group_message(data, users=None, message_type="TXT", summary_user=None):
    # logger = logging.getLogger(__name__)
    # logger.error(f"sending message to: {users=}")
    asyncio.run(
        _send_group_message(
            data, users, message_type=message_type, summary_user=summary_user
        )
    )


async def _send_group_message(data, users, message_type="TXT", summary_user=None):
    SEND_TYPE = {
        "TXT": "sendMessage",
        "PHO": "sendPhoto",
    }
    send_method = SEND_TYPE.get(message_type, None)
    if not send_method:
        return False
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{send_method}"
    tasks = []
    for u in users:
        data.update({"chat_id": u.telegram_id})
        task = asyncio.create_task(_send_message(copy.deepcopy(data), url))
        tasks.append(task)
    else:
        if summary_user:
            _ = asyncio.create_task(_send_summary(tasks=tasks, user=summary_user))
    return tasks


async def _send_summary(tasks, user):
    summary_text = "group send summary\n"
    summary_text += "total number of tried messages: {}\n"
    summary_text += "successfully sent messages: {}\n"
    total_number = len(tasks)
    succ = 0
    for t in tasks:
        await t
        if t.result():
            succ += 1
    text = summary_text.format(total_number, succ)
    data = {"text": text, "chat_id": user.telegram_id}
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    res = requests.post(url=url, json=data)
    return res


async def _send_message(data, url):
    res = requests.post(url=url, json=data)
    return res.json().get("ok", False)  # check if the message has sent or not
