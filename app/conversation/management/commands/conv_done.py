from typing import Any
from django.core.management.base import BaseCommand

from conversation.models import Conversation
from bot import utils


class Command(BaseCommand):
    help = "It sets the conversation states to the done state"

    def handle(self, *args: Any, **options: Any):
        convs = Conversation.objects.filter(
            conversation_state__in=["A-ADMIN-APPR", "RA-ADMIN-APPR"]
        )
        text = "وضعیت مکالمه {} به خاتمه یافته تغییر کرد."
        for c in convs:
            if not c.is_waiting_too_long():
                continue
            _text = text.format(c.get_telegram_command())
            users = [c.student.user]
            c.conversation_state = "C-CONVR-DONE"
            c.save()
            utils.send_group_message(data={"text": _text}, users=users)
