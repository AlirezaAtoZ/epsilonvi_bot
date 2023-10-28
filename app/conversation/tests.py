from django.test import TestCase
from conversation.models import Package, StudentPackage, Conversation
from epsilonvi_bot.models import Student, Teacher, Admin, Subject
from user.models import User


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
