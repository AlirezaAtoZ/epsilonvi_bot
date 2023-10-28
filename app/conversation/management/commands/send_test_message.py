from django.core.management.base import BaseCommand, CommandError
from bot import utils


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        utils.send_group_message()
