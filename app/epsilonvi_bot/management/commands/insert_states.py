from django.core.management.base import BaseCommand, CommandError
from epsilonvi_bot.states import States
from bot.models import State



class Command(BaseCommand):
    def handle(self):
        state = State.objects.create(name="UNIDF_start")
        self.stdout(self.style.SUCCESS(f'done!\nstates: {state.name}'))