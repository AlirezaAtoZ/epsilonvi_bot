from django.core.management.base import BaseCommand, CommandError
from epsilonvi_bot.states import (
    UNIDFWelcomeState,
    UNIDFEditInfoState,
    UNIDFEditInfoNameState,
)
from bot.models import State


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        states = [UNIDFWelcomeState, UNIDFEditInfoState, UNIDFEditInfoNameState]
        for state in states:
            new_model, created = State.objects.get_or_create(name=state.name)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"new model: {new_model} has created")
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(f"model: {new_model} already existed!")
                )
        self.stdout.write(self.style.SUCCESS(f"done!"))
