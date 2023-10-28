from typing import Any
from django.core.management.base import BaseCommand, CommandError
from app.urls import urlpatterns
import requests
import os
import json


class Command(BaseCommand):
    help = "sets bot commands"
    # TODO: softcode it!
    secret_token = os.environ.get('EPSILONVI_DEV_SECRET_TOKEN')
    set_webhook_url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/setMyCommands'

    def handle(self, *args: Any, **options: Any):
        data = {
            "commands": [
                {
                    "command": "start",
                    "description": "starts the bot"
                }
            ]
        }
        res = requests.post(url=self.set_webhook_url, json=data)
        
        if not res.ok:
            raise CommandError(str(res.json()))

        data = res.json()
        self.stdout.write(self.style.SUCCESS(data))