from django.core.management.base import BaseCommand, CommandError
from bot.models import State
from epsilonvi_bot.states.state_manager import StateManager


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        states = StateManager.state_mapping.keys()

        for state in states:
            new_model, created = State.objects.get_or_create(name=state)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"new model: {new_model} has created")
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(f"model: {new_model} already existed!")
                )
        self.stdout.write(self.style.SUCCESS(f"done!"))
