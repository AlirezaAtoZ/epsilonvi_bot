from datetime import datetime

from django.db import models

from user import models as usr_models
from bot import models as bot_models
from epsilonvi_bot import models as eps_models


class Package(models.Model):
    name = models.CharField(max_length=128, default="")
    number_of_questions = models.IntegerField(default=0)
    FIELD_CHOICES = [
        ("MTH", "ریاضی"),
        ("BIO", "تجربی"),
        ("ECO", "انسانی"),
        ("GEN", "عمومی"),
        ("SPC", "نخصصی"),
    ]
    field = models.CharField(max_length=3, choices=FIELD_CHOICES, default="GEN")

    subjects = models.ManyToManyField(eps_models.Subject)
    price = models.BigIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=False)

    def __str__(self) -> str:
        text = str(self.number_of_questions)
        text += " سوال "
        if self.field == "GEN":
            text += "دروس عمومی"
        elif self.field == "SPC":
            text += "دروس تخصصی"
        else:
            text += "از دروس تخصصی رشته"
            text += self.get_field_display()
        return text


class StudentPackage(models.Model):
    student = models.ForeignKey(eps_models.Student, on_delete=models.CASCADE)
    package = models.ForeignKey("Package", on_delete=models.CASCADE)

    asked_questions = models.IntegerField(default=0)
    paid_price = models.BigIntegerField(default=0)

    is_done = models.BooleanField(default=False)

    purchased_date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.package} {self.student.user} {self.asked_questions} of {self.package.number_of_questions}"


class Conversation(models.Model):
    student_package = models.ForeignKey("StudentPackage", on_delete=models.CASCADE)
    subject = models.ForeignKey(eps_models.Subject, on_delete=models.CASCADE)

    student = models.ForeignKey(eps_models.Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(eps_models.Teacher, on_delete=models.CASCADE)

    admins = models.ManyToManyField(
        eps_models.Admin, related_name="all_ineracted_admins"
    )

    question = models.ManyToManyField(bot_models.Message, related_name="question")
    question_date = models.DateTimeField(auto_now_add=True)
    question_approved_by = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="question_approved_by_admin",
    )

    answer = models.ManyToManyField(bot_models.Message, related_name="answer")
    answer_date = models.DateTimeField(null=True, blank=True)
    answer_approved_by = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="answer_approved_by_admin",
    )

    re_question = models.ManyToManyField(bot_models.Message, related_name="re_question")
    re_question_date = models.DateTimeField(auto_now_add=True)
    re_question_approved_by = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="re_question_approved_by_admin",
    )

    re_answer = models.ManyToManyField(bot_models.Message, related_name="re_answer")
    re_answer_date = models.DateTimeField(null=True, blank=True)
    re_answer_approved_by = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="re_answer_approved_by_admin",
    )

    rate = models.FloatField(null=True, blank=True)
    is_done = models.BooleanField(default=False)

    CONVERSATION_STATES = [
        {"ZERO", "درفت"},
        ("Q-W8-ADMIN", "در انتظار تایید ادمین"),
        ("Q-W8-TCHER", "در انتظار پاسخ دبیر"),
        ("A-W8-ADMIN", "در انتظار تایید ادمین"),
        ("A-W8-STDNT", "پاسخ خوانده نشده"),
        ("A-OK", "خاتمه یافته"),
        ("RQ-W8-ADMIN", "در انتظار تایید ادمین"),
        ("RQ-W8-TCHER", "در انتظار پاسخ دبیر"),
        ("RA-W8-ADMIN", "در انتظار تایید ادمین"),
        ("RA-W8-STDNT", "پاسخ خوانده نشده"),
        ("RA-CLOSED", "خاتمه یافته"),
    ]
    conversation_state = models.CharField(
        max_length=11, choices=CONVERSATION_STATES, default="ZERO"
    )

    def __str__(self) -> str:
        return f"{self.student}"
    
    def _get_telegram_command(self):
        return f"/conv{self.pk}"
