import mock
from datetime import datetime
from django.test import TestCase
from .models import TeacherPayment, Invoice
from .zarinpal import Zarinpal
from epsilonvi_bot.models import Student, Teacher, Subject, Admin
from conversation.models import Package, StudentPackage, Conversation
from user.models import User


class TeacherPaymentTestCase(TestCase):
    def setUp(self) -> None:
        self.subject = Subject.objects.create(name="subject")

        self.package = Package.objects.create(
            name="package", number_of_questions=10, price=20_000_000
        )
        self.package.subjects.add(self.subject)

        self.user_student = User.objects.create(telegram_id="student", name="student")
        self.student = Student.objects.create(user=self.user_student)

        self.user_teacher = User.objects.create(telegram_id="teacher", name="teacher")
        self.teacher = Teacher.objects.create(user=self.user_teacher)
        self.teacher.subjects.add(self.subject)

        self.user_teacher2 = User.objects.create(
            telegram_id="teacher2", name="teacher2"
        )
        self.teacher2 = Teacher.objects.create(user=self.user_teacher2)
        self.teacher2.subjects.add(self.subject)

        self.user_admin = User.objects.create(telegram_id="admin", name="admin")
        self.admin = Admin.objects.create(user=self.user_admin)

        self.student_package = StudentPackage.objects.create(
            student=self.student, package=self.package
        )
        return super().setUp()

    def test_payment_model(self):
        tp = TeacherPayment.objects.create(teacher=self.teacher, amount=100_000_000)
        self.assertEqual(tp.teacher, self.teacher)
        self.assertEqual(tp.amount, 100_000_000)
        self.assertEqual(tp.date.day, datetime.now().day)

    def test_to_pay(self):
        c1 = Conversation.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
            student_package=self.student_package,
            is_done=True,
            is_paid=True,
        )
        c2 = Conversation.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
            student_package=self.student_package,
            is_done=True,
            is_paid=False,
        )
        c3 = Conversation.objects.create(
            student=self.student,
            teacher=self.teacher2,
            subject=self.subject,
            student_package=self.student_package,
            is_done=True,
            is_paid=False,
        )
        get_list = Conversation.get_teachers_payments_list()
        ref_list = {
            self.teacher.user.telegram_id: 1_400_000,
            self.teacher2.user.telegram_id: 1_400_000,
        }
        self.assertEqual(get_list, ref_list)


class InvoiceTestCase(TestCase):
    def setUp(self) -> None:
        self.subject = Subject.objects.create(name="subject")

        self.package = Package.objects.create(
            name="package", number_of_questions=10, price=20_000_000
        )
        self.package.subjects.add(self.subject)

        self.user_student = User.objects.create(telegram_id="student", name="student")
        self.student = Student.objects.create(user=self.user_student)

        self.user_teacher = User.objects.create(telegram_id="teacher", name="teacher")
        self.teacher = Teacher.objects.create(user=self.user_teacher)
        self.teacher.subjects.add(self.subject)

        self.user_teacher2 = User.objects.create(
            telegram_id="teacher2", name="teacher2"
        )
        self.teacher2 = Teacher.objects.create(user=self.user_teacher2)
        self.teacher2.subjects.add(self.subject)

        self.user_admin = User.objects.create(telegram_id="admin", name="admin")
        self.admin = Admin.objects.create(user=self.user_admin)

        self.student_package = StudentPackage.objects.create(
            student=self.student, package=self.package
        )
        return super().setUp()

    def test_description_on_creation(self):
        # input()
        invoice = Invoice.objects.create(
            student_package=self.student_package,
            amount=self.student_package.package.price,
        )
        self.assertNotEqual(invoice.description, "توضیحات")

    def test_zarinpal_payment_gateway(self):
        # TODO add mock for request post for none sandbox situations
        invoice = Invoice.objects.create(
            student_package=self.student_package,
            amount=self.student_package.package.price,
        )

        zp = Zarinpal(invoice=invoice)
        self.assertRegexpMatches(
            zp.get_payment_gateway(), r"https://[\w]+.zarinpal.com/pg/StartPay/[\d]+"
        )
