from datetime import timedelta
from django.utils import timezone
from django.core.management import BaseCommand

from conversation.models import Conversation
from conversation.handlers import ConversationStateHandler
from bot import utils


class Command(BaseCommand):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        q = Conversation.objects.filter(teacher__isnull=False, answer__isnull=True)
        now = timezone.now()
        warn_limit = now - timedelta(minutes=15)
        del_limit = now - timedelta(minutes=30)
        warn_un_answered = q.filter(answer_date__lt=warn_limit).exclude(
            answer_date__lt=del_limit
        )
        del_un_answered = q.filter(answer_date__lt=del_limit)

        # warn teachers
        for conversation in warn_un_answered:
            # print(f"warn {conversation.pk}")
            text = f"شما مکالمه {conversation.get_telegram_command()} را انتخاب نموده اید اما پاسخی برای آن ارسال نکرده اید. "
            text += "در صورت عدم پاسخ شما تا ۱۵ دقیقه دیگر این سوال از لیست سوالات فعال شما حذف خواهد شد."
            message = {"text": text}
            utils.send_group_message(message, [conversation.teacher.user])
        
        for conversation in del_un_answered:
            # print(f"del {conversation.pk}")
            text = f"مکالمه {conversation.get_telegram_command()} از لیست مکالمه های شما حذف شد."
            message = {"text": text}
            utils.send_group_message(message, [conversation.teacher.user])
            # conversation.conversation_state = "Q-ADMIN-APPR"
            conversation.teacher = None
            conversation.answer.all().delete()
            conversation.answer_date = None
            conversation.save()
            csh = ConversationStateHandler(conversation)
            csh._handle_q_stdnt_comp(action="approve")

