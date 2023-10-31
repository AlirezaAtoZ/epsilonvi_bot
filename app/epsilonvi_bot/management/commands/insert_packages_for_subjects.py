from django.core.management.base import BaseCommand, CommandError

# from epsilonvi_bot import models as eps_models
from epsilonvi_bot.models import Subject

# from conversation import models as conv_models
from conversation.models import Package


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # create single packages
        subjects = Subject.objects.filter(
            is_active=True, field__in=["MTH", "BIO", "ECO"]
        )
        sng_pcks = subjects.values("field", "group").distinct()
        for sub in sng_pcks:
            pck10, _ = Package.objects.get_or_create(
                name=sub["group"],
                number_of_questions=10,
                field=sub["field"],
                is_active=True,
                package_type="SNG",
                price=30_000,
            )
            pck30, _ = Package.objects.get_or_create(
                name=sub["group"],
                number_of_questions=30,
                field=sub["field"],
                is_active=True,
                package_type="SNG",
                price=60_000,
            )
            subs = Subject.objects.filter(group=sub["group"], field=sub["field"])
            pck10.subjects.add(*subs)
            pck30.subjects.add(*subs)

        # create general packages
        subjects = Subject.objects.filter(field="GEN")
        pck10, _ = Package.objects.get_or_create(
            name="درس های عمومی",
            number_of_questions=10,
            field="GEN",
            is_active=True,
            package_type="ALL",
            price=25_000,
        )
        pck10.subjects.add(*subjects)
        pck30, _ = Package.objects.get_or_create(
            name="درس های عمومی",
            number_of_questions=30,
            field="GEN",
            is_active=True,
            package_type="ALL",
            price=45_000,
        )
        pck30.subjects.add(*subjects)
        # create specilized all packages
        subjects = Subject.objects.filter(field="MTH")
        pck10, _ = Package.objects.get_or_create(
            name="جامع رشته ریاضی",
            number_of_questions=10,
            field="MTH",
            is_active=True,
            package_type="ALL",
            price=40_000,
        )
        pck10.subjects.add(*subjects)
        pck30, _ = Package.objects.get_or_create(
            name="جامع رشته ریاضی",
            number_of_questions=30,
            field="MTH",
            is_active=True,
            package_type="ALL",
            price=90_000,
        )
        pck30.subjects.add(*subjects)
        subjects = Subject.objects.filter(field="BIO")
        pck10, _ = Package.objects.get_or_create(
            name="جامع رشته تجربی",
            number_of_questions=10,
            field="BIO",
            is_active=True,
            package_type="ALL",
            price=40_000,
        )
        pck10.subjects.add(*subjects)
        pck30, _ = Package.objects.get_or_create(
            name="جامع رشته تجربی",
            number_of_questions=30,
            field="BIO",
            is_active=True,
            package_type="ALL",
            price=90_000,
        )
        pck30.subjects.add(*subjects)
        subjects = Subject.objects.filter(field="ECO")
        pck10, _ = Package.objects.get_or_create(
            name="جامع رشته انسانی",
            number_of_questions=10,
            field="ECO",
            is_active=True,
            package_type="ALL",
            price=40_000,
        )
        pck10.subjects.add(*subjects)
        pck30, _ = Package.objects.get_or_create(
            name="جامع رشته انسانی",
            number_of_questions=30,
            field="ECO",
            is_active=True,
            package_type="ALL",
            price=90_000,
        )
        pck30.subjects.add(*subjects)
