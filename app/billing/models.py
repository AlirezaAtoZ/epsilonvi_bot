from django.db import models
from epsilonvi_bot.models import Teacher
from conversation.models import Conversation


class TeacherPayment(models.Model):
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, blank=True, null=True
    )
    amount = models.BigIntegerField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.teacher} {self.date} {self.amount}"


def all_teachers_unpaid_list():
    done_conversations = Conversation.objects.filter(is_done=True, is_paid=False)
    unpaid_dict = {}
    for conv in done_conversations:
        conv_value = conv.student_package.package.price / conv.student_package.package.number_of_questions
        conv_value *= .7
        telegram_id = conv.teacher.user.telegram_id
        _cur_val = unpaid_dict.get(telegram_id, None)
        _total = 0 if not _cur_val else _cur_val.get("total") + conv_value
        _d = {str(telegram_id), _total}
        unpaid_dict.update(_d)
    return unpaid_dict
        
