from django.db import models
from bot import models as bot_models
from user import models as usr_models


class Subject(models.Model):
    name = models.CharField(max_length=64)

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
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} {self.get_grade_display()} {self.get_field_display()}"


class Teacher(models.Model):
    user = models.OneToOneField(usr_models.User, on_delete=models.CASCADE)
    subjects = models.ManyToManyField("Subject", blank=True)

    is_active = models.BooleanField(default=False)
    credit_card_number = models.CharField(max_length=16, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user}"


class Student(models.Model):
    user = models.OneToOneField(usr_models.User, on_delete=models.CASCADE)

    GRADE_CHOICES = [
        ("UNKWN", "نامشخص"),
        ("10MTH", "دهم ریاضی"),
        ("11MTH", "یازدهم ریاضی"),
        ("12MTH", "دوازدهم ریاضی"),
        ("10BIO", "دهم تجربی"),
        ("11BIO", "یازدهم تجربی"),
        ("12BIO", "دوازدهم تجربی"),
        ("10ECO", "دهم انسانی"),
        ("11ECO", "یازدهم انسانی"),
        ("12ECO", "دوازدهم انسانی"),
        ("OTHER", "سایر"),
    ]
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES, default="UNKWN")
    is_active = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user.name} {self.get_grade_display()}"


class Admin(models.Model):
    user = models.OneToOneField(usr_models.User, on_delete=models.CASCADE)

    is_active = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user}"
