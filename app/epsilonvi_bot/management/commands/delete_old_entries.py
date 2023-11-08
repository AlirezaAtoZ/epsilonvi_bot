from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bot.models import UpdateID
from epsilonvi_bot.models import SecretCode

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # delete old secret codes
        limit = timezone.now() - timedelta(days=3)
        scs = SecretCode.objects.filter(created__lt=limit)
        scs.delete()

        # TODO delete old updates
