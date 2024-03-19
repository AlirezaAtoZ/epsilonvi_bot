import json

from django.core.management.base import BaseCommand

from user.models import User
from epsilonvi_bot import models as eps_models
from epsilonvi_bot import permissions as perms


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("telegram_id", type=str)

    def handle(self, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        if not telegram_id:
            self.stderr.write("No Telegram ID has provided!")
            return
        user = User.objects.filter(telegram_id=telegram_id).first()
        if not user:
            self.stderr.write("User not found!")
            return

        admin = eps_models.Admin.create_admin(user)
        all_permissions = [perms.SendGroupMessage.name,
                           perms.CanApproveConversation.name,
                           perms.AddAdmin.name,
                           perms.AddTeacher.name,
                           perms.CanPayTeacher.name]

        permissions = json.loads(admin.permissions)
        permissions = list(set(permissions + all_permissions))
        admin.permissions = json.dumps(permissions)
        admin.save()

        self.stdout.write(f"Successfully created super-admin: {admin} with permissions: {permissions}")
