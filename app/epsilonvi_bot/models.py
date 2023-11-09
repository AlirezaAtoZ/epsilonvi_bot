import json
import random
import string

from django.db import models
from bot import models as bot_models
from user import models as usr_models
from epsilonvi_bot import permissions as perm
from conversation.models import Conversation

random.random()


class Subject(models.Model):
    name = models.CharField(max_length=64, default="")
    group = models.CharField(max_length=64, default="")

    GRADE_CHOICES = [
        ("10", "دهم"),
        ("11", "یازدهم"),
        ("12", "دوازدهم"),
        ("ALL", "همه"),
    ]
    grade = models.CharField(max_length=5, choices=GRADE_CHOICES, default="ALL")

    FIELDS = ("MTH", "BIO", "ECO", "GEN")
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

    def diplay_name_without_field(self):
        return f"{self.name} {self.get_grade_display()}"


class Teacher(models.Model):
    user = models.OneToOneField(usr_models.User, on_delete=models.CASCADE)
    subjects = models.ManyToManyField("Subject", blank=True)

    permissions = models.TextField(default="")
    is_active = models.BooleanField(default=False)
    credit_card_number = models.CharField(max_length=16, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user}"
    
    def get_unpaid_conversations(self):
        convs = Conversation.objects.filter(teacher=self, is_done=True, is_paid=False)
        return convs


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

    credit_card_number = models.CharField(max_length=16, null=True, blank=True)
    permissions = models.TextField(default="")
    is_active = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user}"

    @classmethod
    def create_admin(cls, user):
        permissions = [perm.IsAdmin.name, perm.AddAdmin.name]
        _json = json.dumps(permissions)
        admin = cls.objects.create(user=user, is_active=True, permissions=_json)
        return admin

def generate_code():
    letters = string.ascii_lowercase
    word = "".join(random.choice(letters) for _ in range(5))
    return word


class SecretCode(models.Model):
    code = models.CharField(max_length=5, default=generate_code, editable=False)
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE)
    USAGE_CHOICES = [("ADMIN", "admin"), ("TCHER", "teacher")]
    usage = models.CharField(max_length=5, choices=USAGE_CHOICES, default="ADMIN")
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.code} by {self.admin.user} for {self.usage}"

    def display_command(self):
        return f"https://t.me/epsilonvibot?start=action_{self.get_usage_display()}_{self.code}"


class SpecialMessage(models.Model):
    message = models.ForeignKey(
        bot_models.Message, on_delete=models.CASCADE, blank=True, null=True
    )
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, blank=True, null=True)
    is_sent = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
