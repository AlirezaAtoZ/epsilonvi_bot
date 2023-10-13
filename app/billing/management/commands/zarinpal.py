import requests
from django.core.management.base import BaseCommand, CommandError
from bot.models import State
from epsilonvi_bot.states.state_manager import StateManager


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        url = "https://api.zarinpal.com/pg/v4/payment/request.json"
        _data = {
            "merchant_id": "c4f7bcfb-5996-4e44-a098-6fb90a953dd1",
            "amount": 100000,
            "description": "test_001",
            "callback_url": "https://google.com",
        }
        res = requests.post(url=url, json=_data)
        msg = f"{res.status_code=}\n"
        msg += f"{res.text=}"
        self.stdout.write(msg=msg)
