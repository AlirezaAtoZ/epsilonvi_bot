from django.core.management.base import BaseCommand, CommandError
from bot.models import State
from epsilonvi_bot.states import States


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        states = [
            States.UNIDF_edit_info_grade, States.UNIDF_edit_info_phone_number
        ]
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
