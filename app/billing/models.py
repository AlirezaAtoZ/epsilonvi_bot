from collections.abc import Iterable
from datetime import datetime
from django.db import models
from django.conf import settings
from epsilonvi_bot.models import Teacher
from conversation.models import Conversation, StudentPackage


class TeacherPayment(models.Model):
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, blank=True, null=True
    )
    amount = models.BigIntegerField()
    date = models.DateTimeField(auto_now_add=True)
    conversations = models.ManyToManyField("conversation.Conversation", blank=True)

    def __str__(self) -> str:
        return f"{self.teacher} {self.date} {self.amount}"
    
    def get_teacher_info_display(self):
        text = f"مقدار پرداخت شده: {self.amount}\n"
        text += f"تاریخ پرداخت: {self.date.date()}\n"
        l = ""
        for c in self.conversations.all():
            l += c.get_telegram_command() + ""
        text += f"پرداخت مربوط به مکالمات: {l}\n"
        return text
    
    def get_admin_info_display(self):
        text = f"دبیر: {self.teacher.user.name}\n"
        text += f"مقدار پرداخت شده: {self.amount}\n"
        text += f"تاریخ پرداخت: {self.date.date()}\n"
        return text


class Invoice(models.Model):
    is_paid = models.BooleanField(default=False)
    is_pending = models.BooleanField(default=False)

    STATUS_CHOICES = [
        [0, "نامشحص"],
        [-1, "اطلاعات ارسال شده ناقص است"],
        [-2, "IP و يا مرچنت كد پذيرنده صحيح نيست."],
        [
            -3,
            "با توجه به محدوديت هاي شاپرك امكان پرداخت با رقم درخواست شده ميسر نمي باشد.",
        ],
        [-4, "سطح تاييد پذيرنده پايين تر از سطح نقره اي است"],
        [-11, "درخواست مورد نظر يافت نشد"],
        [-12, "امكان ويرايش درخواست ميسر نمي باشد."],
        [-21, "هيچ نوع عمليات مالي براي اين تراكنش يافت نشد."],
        [-22, "تراكنش نا موفق ميباشد."],
        [-33, "رقم تراكنش با رقم پرداخت شده مطابقت ندارد."],
        [-34, "سقف تقسيم تراكنش از لحاظ تعداد يا رقم عبور نموده است"],
        [-40, "جازه دسترسي به متد مربوطه وجود ندارد"],
        [-41, "اطلاعات ارسال شده مربوط به AdditionalData غيرمعتبر ميباشد."],
        [
            -42,
            "مدت زمان معتبر طول عمر شناسه پرداخت بايد بين 30 دقيه تا 45 روز مي باشد.",
        ],
        [-54, "درخواست مورد نظر آرشيو شده است."],
        [100, "عمليات با موفقيت انجام گرديده است."],
        [
            101,
            "عمليات پرداخت موفق بوده و قبلا PaymentVerification تراكنش انجام شده است.",
        ],
    ]
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    amount = models.BigIntegerField(default=-1)
    description = models.TextField(default="توضیحات")
    authority = models.CharField(max_length=36, null=True, blank=True)
    ref_id = models.CharField(max_length=512, blank=True, null=True)
    payment_url = models.URLField(blank=True, null=True)
    callback_url = models.URLField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    paid_date = models.DateTimeField(blank=True, null=True)

    student_package = models.OneToOneField(
        "conversation.StudentPackage", on_delete=models.CASCADE, null=True, blank=True
    )

    def display_short_info(self):
        status = "موفق ✅" if self.is_paid else "ناموفق ❌"
        text = f"توضیحات: {self.description} وضعیت: {status}\n"
        return text

    def display_detailed_info(self):
        status = "موفق" if self.is_paid else "ناموفق"
        text = (
            f"دانش آموز: {self.student_package.student.user.get_name_inline_link()}\n"
        )
        text += f"بسته: {self.student_package.package.name}\n"
        text += f"مقدار: {self.amount}\n"
        text += f"وضعیت پرداخت: {status}\n"
        text += f"تاریخ درخواست: {self.date}\n"
        return text

    @classmethod
    def get_all(cls, **kwargs):
        _q = cls.objects.filter(**kwargs)
        return _q

    @classmethod
    def get_successful(cls, **kwargs):
        _q = cls.objects.filter(is_paid=True, **kwargs)
        return _q

    @staticmethod
    def display_list(query):
        text = ""
        if query.exists():
            for idx, inv in enumerate(query):
                text += f"{idx+1} {inv.display_short_info()}"
        else:
            text = "داده ای برای نمایش وجود ندارد."
        return text

    def _get_description(self):
        text = f"خرید بسته {self.student_package.package} {self.student_package.package.number_of_questions} به مبلغ: {self.student_package.package.price}"
        return text

    def save(self, *args, **kwargs) -> None:
        if not self.pk:
            self.description = self._get_description()
        return super().save(*args, **kwargs)

    def set_callback_url(self):
        if self.callback_url:
            return
        if settings.IS_DEV:
            url = f"https://epsilonvi.ir/dev/invoice/{self.pk}/verify/"
        else:
            url = f"https://epsilonvi.ir/invoice/{self.pk}/verify/"
        self.callback_url = url
        self.save()

    def get_verify_telegram_url(self):
        return f"https://t.me/{settings.BOT_USERNAME}?start=action_verify_{self.pk}"
