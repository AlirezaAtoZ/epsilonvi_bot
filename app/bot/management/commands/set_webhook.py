from typing import Any
from django.core.management.base import BaseCommand, CommandError
from app.urls import urlpatterns
import requests
import os
import json


class Command(BaseCommand):
    help = "sets the webhook url"
    # TODO: softcode it!
    webhook_url = 'https://epsilonvi.ir/bot-webhook-63af1eda-28f9-4f21-b8df-fb73453f9892'
    secret_token = os.environ.get('EPSILONVI_DEV_SECRET_TOKEN')
    set_webhook_url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/setWebhook'
    params = {
	'url': webhook_url,
	'X-Telegram-Bot-Api-Secret-Token': secret_token}

    def handle(self, *args: Any, **options: Any):
        res = requests.get(url=self.set_webhook_url, params=self.params)
        
        if not res.ok:
            raise CommandError(str(res.json()))

        data = res.json()
        self.stdout.write(self.style.SUCCESS(data['description']))
