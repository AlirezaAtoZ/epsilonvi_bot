from datetime import datetime
from pyexpat import model

from django.db import models

from user import models as usr_models
from bot import models as bot_models
from epsilonvi_bot import models as eps_models


class Package(models.Model):
    name = models.CharField(max_length=128, default="")

    PACKAGE_TYPES = [
        ("SNG", "نک درس"),
        ("ALL", "جامع"),
    ]
    package_type = models.CharField(
        max_length=3, choices=PACKAGE_TYPES, blank=True, null=True
    )

    number_of_questions = models.IntegerField(default=0)

    GRADE_CHOICES = [
        ("10", "دهم"),
        ("11", "یازدهم"),
        ("12", "دوازدهم"),
        ("ALL", "همه"),
    ]
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES, default="ALL")

    FIELD_CHOICES = [
        ("MTH", "ریاضی"),
        ("BIO", "تجربی"),
        ("ECO", "انسانی"),
        ("GEN", "عمومی"),
    ]
    field = models.CharField(max_length=3, choices=FIELD_CHOICES, default="GEN")

    subjects = models.ManyToManyField(eps_models.Subject)
    price = models.BigIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=False)

    def __str_single__(self):
        text = str(self.number_of_questions)
        text += " سوال "
        text += f"از درس {self.subjects.all()[0]}"
        return text

    def __str_all__(self):
        text = str(self.number_of_questions)
        text += " سوال "
        if self.field == "GEN":
            text += "دروس عمومی"
        elif self.field == "SPC":
            text += "دروس تخصصی"
        else:
            text += "از دروس تخصصی رشته "
            text += self.get_field_display()
        return text

    def __str__(self) -> str:
        if self.package_type == "ALL":
            return self.__str_all__()
        else:
            return self.__str_single__()

    def display_detailed(self):
        text = f"{self.name}\n"
        text += f"تعداد سوال: {self.number_of_questions}\n"
        text += f"قیمت: {self.price} تومان\n"
        text += f"درس های موجود در این بسته:\n"
        for subj in self.subjects.all():
            text += f"-{subj.diplay_name_without_field()} "
        return text


class StudentPackage(models.Model):
    student = models.ForeignKey(eps_models.Student, on_delete=models.CASCADE)
    package = models.ForeignKey(
        "Package", on_delete=models.CASCADE, related_name="studentpackage"
    )

    asked_questions = models.IntegerField(default=0)
    paid_price = models.BigIntegerField(default=0)

    is_done = models.BooleanField(default=False)
    is_pending = models.BooleanField(default=True)

    purchased_date = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.package} {self.student.user} {self.asked_questions} of {self.package.number_of_questions}"

    def increase_asked(self):
        if self.asked_questions < self.package.asked_questions:
            self.asked_questions += 1
            return True
        else:
            return False


class Conversation(models.Model):
    student_package = models.ForeignKey("StudentPackage", on_delete=models.CASCADE)
    subject = models.ForeignKey(eps_models.Subject, on_delete=models.CASCADE)

    student = models.ForeignKey(eps_models.Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        eps_models.Teacher, on_delete=models.CASCADE, blank=True, null=True
    )

    admins = models.ManyToManyField(
        eps_models.Admin, related_name="all_ineracted_admins"
    )

    question = models.ManyToManyField(bot_models.Message, related_name="question")
    question_date = models.DateTimeField(auto_now_add=True)
    question_approved_by = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="question_approved_by_admin",
        blank=True,
        null=True,
    )

    answer = models.ManyToManyField(bot_models.Message, related_name="answer")
    answer_date = models.DateTimeField(null=True, blank=True)
    answer_approved_by = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="answer_approved_by_admin",
        blank=True,
        null=True,
    )

    re_question = models.ManyToManyField(bot_models.Message, related_name="re_question")
    re_question_date = models.DateTimeField(auto_now_add=True)
    re_question_approved_by = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="re_question_approved_by_admin",
        blank=True,
        null=True,
    )

    re_answer = models.ManyToManyField(bot_models.Message, related_name="re_answer")
    re_answer_date = models.DateTimeField(null=True, blank=True)
    re_answer_approved_by = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="re_answer_approved_by_admin",
        blank=True,
        null=True,
    )

    admin_response = models.ManyToManyField(
        bot_models.Message, related_name="admin_response"
    )
    working_admin = models.ForeignKey(
        eps_models.Admin,
        on_delete=models.CASCADE,
        related_name="wroking_admin",
        blank=True,
        null=True,
    )

    rate = models.FloatField(null=True, blank=True)
    is_done = models.BooleanField(default=False)

    CONVERSATION_STATES = (
        ("Z-UNKWN-ZERO", ""),
        ("Q-STDNT-DRFT", ""),
        ("Q-STDNT-COMP", ""),
        ("Q-ADMIN-APPR", ""),
        ("Q-ADMIN-DENY", ""),
        ("Q-ADMIN-DRFT", ""),
        ("Q-ADMIN-COMP", ""),
        ("Q-STDNT-DEND", ""),
        ("A-TCHER-DRFT", ""),
        ("A-TCHER-COMP", ""),
        ("A-ADMIN-APPR", ""),
        ("A-ADMIN-DENY", ""),
        ("A-ADMIN-DRFT", ""),
        ("A-ADMIN-COMP", ""),
        ("A-TCHER-DEND", ""),
        ("A-STDNT-APPR", ""),
        ("A-STDNT-DENY", ""),
        ("RQ-STDNT-DRFT", ""),
        ("RQ-STDNT-COMP", ""),
        ("RQ-ADMIN-APPR", ""),
        ("RQ-ADMIN-DENY", ""),
        ("RQ-ADMIN-DRFT", ""),
        ("RQ-ADMIN-COMP", ""),
        ("RQ-STDNT-DEND", ""),
        ("RA-TCHER-DRFT", ""),
        ("RA-TCHER-COMP", ""),
        ("RA-ADMIN-APPR", ""),
        ("RA-ADMIN-DENY", ""),
        ("RA-ADMIN-DRFT", ""),
        ("RA-ADMIN-COMP", ""),
        ("RA-TCHER-DEND", ""),
        ("C-CONVR-DONE", ""),
    )
    conversation_state = models.CharField(
        max_length=13, choices=CONVERSATION_STATES, default="Z-NKNWN-ZERO"
    )

    def __str__(self) -> str:
        return f"{self.student}"

    def get_telegram_command(self):
        return f"/conv_{self.pk}"

    def set_next_state(self):
        idx = 0
        for i, s in enumerate(self.CONVERSATION_STATES):
            _s = sorted(s)
            if self.conversation_state == _s[0]:
                idx = i
        # print(f"{idx=}")
        if idx < 11:
            _cs = self.CONVERSATION_STATES[idx + 1][0]
            # print(f"{_cs}")
            self.conversation_state = _cs
            # self.save()

    def set_prev_state(self):
        idx = 0
        for i, s in enumerate(self.CONVERSATION_STATES):
            _s = sorted(s)
            if self.conversation_state == _s[0]:
                idx = i
        if idx > 1:
            self.conversation_state = self.CONVERSATION_STATES[idx - 1][0]
            # self.save()
