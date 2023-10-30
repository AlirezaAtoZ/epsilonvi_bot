from typing import Any
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.urls import reverse
import requests


class Command(BaseCommand):
    help = "sets the webhook url"

    secret_token = settings.TELEGRAM_SECRET_CODE
    base_url = "https://epsilonvi.ir"
    url = base_url + "/dev" if settings.IS_DEV else base_url
    webhook_url = url + reverse("bot-webhook")

    set_webhook_url = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook'
    params = {"url": webhook_url, "secret_token": secret_token}

    def handle(self, *args: Any, **options: Any):
        res = requests.post(url=self.set_webhook_url, params=self.params)

        if not res.ok:
            raise CommandError(str(res.json()))

        data = res.json()
        self.stdout.write(self.style.SUCCESS(data["description"]))
