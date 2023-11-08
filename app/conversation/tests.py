from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from conversation.models import Package, StudentPackage, Conversation
from epsilonvi_bot.models import Student, Teacher, Admin, Subject
from user.models import User
from bot.models import Message


class ConversationHanderTestCase(TestCase):
    def setUp(self) -> None:
        self.subject = Subject.objects.create(name="subject")

        self.package = Package.objects.create(name="package")
        self.package.subjects.add(self.subject)

        self.user_student = User.objects.create(telegram_id="student", name="student")
        self.student = Student.objects.create(user=self.user_student)

        self.user_teacher = User.objects.create(telegram_id="teacher", name="teacher")
        self.teacher = Teacher.objects.create(user=self.user_teacher)
        self.teacher.subjects.add(self.subject)

        self.user_admin = User.objects.create(telegram_id="admin", name="admin")
        self.admin = Admin.objects.create(user=self.user_admin)

        self.student_package = StudentPackage.objects.create(
            student=self.student, package=self.package
        )

        return super().setUp()

    def test_converstion_state(self):
        conversation = Conversation.objects.create(
            student=self.student,
            student_package=self.student_package,
            subject=self.subject,
        )
        self.assertEqual(conversation.student, self.student)


class ConversationTestCase(TestCase):
    def setUp(self) -> None:
        self.subject = Subject.objects.create(name="subject")

        self.package = Package.objects.create(name="package")
        self.package.subjects.add(self.subject)

        self.user_student = User.objects.create(telegram_id="student", name="student")
        self.student = Student.objects.create(user=self.user_student)

        self.user_teacher = User.objects.create(telegram_id="teacher", name="teacher")
        self.teacher = Teacher.objects.create(user=self.user_teacher)
        self.teacher.subjects.add(self.subject)

        self.user_admin = User.objects.create(telegram_id="admin", name="admin")
        self.admin = Admin.objects.create(user=self.user_admin)

        self.student_package = StudentPackage.objects.create(
            student=self.student, package=self.package
        )
        return super().setUp()

    def test_get_teacher_payments(self):
        Conversation.get_teachers_payments_list()

    def test_is_waiting_too_long(self):
        conv = Conversation.objects.create(
            student=self.student,
            student_package=self.student_package,
            subject=self.subject,
        )
        message = Message.objects.create(text="test message", message_id=0, chat_id=0)
        yesterday_date = timezone.now() - timedelta(days=1)
        self.assertFalse(conv.is_waiting_too_long())
        self.assertEqual(conv.answer.all().count(), 0)
        self.assertIsNone(conv.answer_date)
        conv.answer.add(message)
        conv.conversation_state = "A-ADMIN-APPR"
        conv.save()
        self.assertEqual(conv.answer.all().first(), message)
        self.assertIsNotNone(conv.answer_date)
        self.assertFalse(conv.is_waiting_too_long())
        conv.answer_date = yesterday_date
        conv.save()
        self.assertTrue(conv.is_waiting_too_long())

        self.assertEqual(conv.re_answer.all().count(), 0)
        self.assertIsNone(conv.re_answer_date)
        conv.re_answer.add(message)
        conv.conversation_state = "RA-ADMIN-APPR"
        conv.save()
        self.assertEqual(conv.re_answer.all().first(), message)
        self.assertIsNotNone(conv.re_answer_date)
        self.assertFalse(conv.is_waiting_too_long())
        conv.re_answer_date = yesterday_date
        conv.save()
        self.assertTrue(conv.is_waiting_too_long())
