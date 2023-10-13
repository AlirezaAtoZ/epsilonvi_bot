from django.core.management.base import BaseCommand, CommandError

from epsilonvi_bot import models as eps_models
from conversation import models as conv_models

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        subjects = eps_models.Subject.objects.filter(is_active=True, field__in=["MTH", "BIO", "ECO"])
        for s in subjects:
            pckg = conv_models.Package.objects.create(
                name="تک درس تخصصی",
                number_of_questions=10,
                field=s.field,
                is_active=True,
                price=30000,
            )
            
            pckg.subjects.add(s)
            pckg.save()
            self.stdout.write(self.style.SUCCESS(f"{s=} created"))

            pckg = conv_models.Package.objects.create(
                name="تک درس تخصصی",
                number_of_questions=30,
                field=s.field,
                is_active=True,
                price=60000,
            )
            pckg.subjects.add(s)
            pckg.save()
            self.stdout.write(self.style.SUCCESS(f"{s=} created"))
