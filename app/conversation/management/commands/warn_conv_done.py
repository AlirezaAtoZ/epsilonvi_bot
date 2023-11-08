from typing import Any
from django.core.management.base import BaseCommand

from conversation.models import Conversation
from bot import utils


class Command(BaseCommand):
    help = "It sends a warning message to all conversations that are answered bit not completed!"

    def handle(self, *args: Any, **options: Any):
        convs = Conversation.objects.filter(
            conversation_state__in=["A-ADMIN-APPR", "RA-ADMIN-APPR"]
        )
        text = "پرسش شما در مکالمه {} پاسخ داده شده.\nاین مکالمه تا پایان امروز به صورت خودکار بسته خواهد شد."
        text += "شما می توانید با انتخاب دستور موجود در همین پیام نسبت به تکمیل یا پیگیری مکالمه اقدام نمایید."

        for c in convs:
            if not c.is_waiting_too_long():
                continue
            user = c.student.user
            users = [user]
            _text = text.format(c.get_telegram_command())
            data = {"text": _text}
            utils.send_group_message(data=data, users=users)
