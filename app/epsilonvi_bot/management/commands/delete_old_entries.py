from django.core.management.base import BaseCommand, CommandError
from bot.models import UpdateID

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        UpdateID.objects.filter()
