from typing import Any
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import requests


class Command(BaseCommand):
    help = "sets the webhook url"
    # TODO: softcode it!

    secret_token = settings.TELEGRAM_SECRECT_CODE
    webhook_url = (
        f"https://epsilonvi.ir/bot-webhook-2ee122b7-5da0-4d9e-981f-d57d0e4103e2"
    )
    set_webhook_url = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook'
    params = {"url": webhook_url, "secret_token": secret_token}

    def handle(self, *args: Any, **options: Any):
        res = requests.post(url=self.set_webhook_url, params=self.params)

        if not res.ok:
            raise CommandError(str(res.json()))

        data = res.json()
        self.stdout.write(self.style.SUCCESS(data["description"]))
