from typing import Any
from django.core.management.base import BaseCommand, CommandError
from app.urls import urlpatterns
import requests


class Command(BaseCommand):
    help = "sets the webhook url"
    # TODO: softcode it!
    webhook_url = 'epsilonvi.ir/bot-webhook-63af1eda-28f9-4f21-b8df-fb73453f9892/'
    secret_token = 'ceb5481d-6c93-4954-b853-cfb31cecb786'
    set_webhook_url = 'https://api.telegram.org/bot600565689:AAFh_EUMqwILLe6sE0jp1lNTVOTQsL2pCvY/setWebhook'
    params = {'X-Telegram-Bot-Api-Secret-Token': secret_token}

    def handle(self, *args: Any, **options: Any) -> str | None:
        res = requests.get(
            url=self.set_webhook_url,
            params=self.params)
        
        data = res.json()

        self.stdout.write(str(data))
        