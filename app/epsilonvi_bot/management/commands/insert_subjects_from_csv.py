import csv

from django.core.management.base import BaseCommand, CommandError

from epsilonvi_bot import models as eps_models


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("file", type=str)

    def handle(self, *args, **kwargs):
        with open(kwargs["file"], "r", encoding="UTF-8") as f:
            csv_reader = csv.reader(f)
            # text = ""
            for name, group, grade, field in csv_reader:
                try:
                    if ["subject", "group", "grade", "field"] == [
                        name,
                        group,
                        grade,
                        field,
                    ]:
                        # continue if it is header row
                        continue
                    subject, new = eps_models.Subject.objects.get_or_create(
                        name=name,
                        group=group,
                        grade=grade,
                        field=field,
                        is_active=True,
                    )
                    if new:
                        self.stdout.write(self.style.SUCCESS(f"{subject=} created"))
                    else:
                        self.stdout.write(
                            self.style.MIGRATE_HEADING(f"{subject=} already exist")
                        )
                except Exception as err:
                    self.stderr.write(str(err))
