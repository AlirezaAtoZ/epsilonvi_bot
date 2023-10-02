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
    name = models.TextField(_('full name'), blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    last_login = models.DateTimeField(_('last login'), blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "telegram_id"

    def __str__(self) -> str:
        return str(self.name) + " " + str(self.telegram_id)

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin
