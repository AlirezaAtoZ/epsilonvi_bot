from django.db import models
from bot import models as bot_models
from user import models as user_models


class Student(models.Model):
    user = models.OneToOneField(user_models.User, on_delete=models.CASCADE)

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
        return f"{self.user.name} {self.grade}"
