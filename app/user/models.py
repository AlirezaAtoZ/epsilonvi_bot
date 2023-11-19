from pyexpat import model
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, telegram_id, password=None):
        if not telegram_id:
            raise ValueError('Telegram ID is required')
        
        user = self.model(telegram_id=telegram_id)
        user.set_password(password)
        user.save(using=self._db)

        return user
    
    def create_superuser(self, telegram_id, password=None):
        user = self.create_user(telegram_id, password=password)
        user.is_superuser = True
        user.is_admin = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    telegram_id = models.CharField(_('telegram ID'), max_length=64, unique=True)
    
    public_id = models.CharField(max_length=64, blank=True, null=True)
    rand_int = models.CharField(max_length=8, blank=True, null=True)

    name = models.TextField(_('full name'), blank=True, null=True)
    phone_number = models.CharField(max_length=12, blank=True, null=True)  # TODO add a validator

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    last_login = models.DateTimeField(_('last login'), blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    # TODO do it with RAM
    lock = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "telegram_id"

    def __str__(self) -> str:
        return str(self.name) + " " + str(self.telegram_id)

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin
    
    def get_name_inline_link(self):
        return f"[{self.name}](tg://user?id={self.telegram_id})"

    def get_student_info_display(self):
        text = "نام:\n"
        if self.name:
            text += f"{self.name}\n"
        text += "شماره موبایل:\n"
        if self.phone_number:
            text += f"{self.phone_number}\n"
        text += "مقطع تحصیلی:\n"
        text += f"{self.student.get_grade_display()}\n"
        return text
