import json

from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from .base import BaseState
from conversation import models as conv_models
from bot import models as bot_models
from epsilonvi_bot import models as eps_models

# TODO remove double queries
# TODO phone number validation error
# TODO add message type like photo handler when message input is available


def print_user_name(user):
    text = f"کاربر {user.name}\n"
    return text


def print_user_detailed(user):
    text = "نام:\n"
    text += f"{user.name}\n"
    text += "شماره موبایل:\n"
    text += f"{user.phone_number}\n"
    text += "مقطع تحصیلی:\n"
    text += f"{user.student.get_grade_display()}\n"
    return text


def print_student_active_packages(user):
    user_packages = conv_models.StudentPackage.objects.filter(
        student__user=user, is_done=False
    )
    text = ""
    if user_packages.count() == 0:
        text = "شما بسته فعالی ندارید."
    for idx, pckg in enumerate(user_packages):
        t = f"{idx}- {pckg.asked_questions}/{pckg.package.__str__()}\n"
        text += t
    return text


def print_student_all_packages_detailed(user):
    pckgs = conv_models.StudentPackage.objects.filter(student__user=user).order_by(
        "purchased_date"
    )
    text = ""
    if pckgs.count() == 0:
        text = "تا کنون بسته ای خریداری نشده.\n"
    else:
        for idx, pckg in enumerate(pckgs):
            t = f"{idx}- {pckg} {pckg.purchased_date}\n"
            text += t
    return text


def print_student_unseen_conversations(user):
    conversations = conv_models.Conversation.objects.filter(
        student__user=user, conversation_state__endswith="STDNT"
    )
    text = ""
    if conversations.count() == 0:
        text = "شما پرسش خوانده نشده ندارید.\n"
    for idx, conv in enumerate(conversations):
        t = f"{idx}- {conv._get_telegram_command()}\n"
        text += t
    return text


def print_student_all_conversations(user):
    convs = conv_models.Conversation.objects.filter(student__user=user).order_by(
        "question_date"
    )
    text = ""
    if convs.count() == 0:
        text = "تا کنون پرسشی پرسیده نشده.\n"
    else:
        for idx, conv in enumerate(convs):
            status = "خاتمه یافته" if conv.is_done else "فعال"
            t = f"{idx}- {conv._get_telegram_command()} {status} {conv.subject}\n"
            text += t
    return text


def print_active_packages():
    pckgs = conv_models.Package.objects.filter(is_active=True)
    text = ""
    if not pckgs.count() == 0:
        for idx, pckg in enumerate(pckgs):
            t = f"{idx}- {pckg}\n"
            text += t
    else:
        text = "درحال حاضر بسته قابل عرضه ای وجود ندارد.\n"
    return text


def get_active_packages():
    pckgs = conv_models.Package.objects.filter(is_active=True)
    _list = []
    for pckg in pckgs:
        name = str(pckg)
        pckg_id = pckg.pk
        _list.append((name, pckg_id))
    return _list


class StudentError(BaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.name = "STDNT_error"

    def get_message(self, chat_id):
        text = "مشکلی پیش آمده مجددا تلاش کنید."
        message = self._get_message_dict(text=text, chat_id=chat_id)
        return message

    def _handle_message(self):
        self.send_message(self.get_message(self.chat_id))
        return HttpResponse("Something went wrong")

    def _handle_callback_query(self):
        self.send_message(self.get_message(self.chat_id))
        return HttpResponse("Something went wrong")


class StudentHome(BaseState):
    name = "STDNT_home"
    text = "صفحه اصلی"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_input_types.append(self.MESSAGE)

        self.expected_states = {
            StudentQuestionManager.name: StudentQuestionManager,
            StudentPackageManager.name: StudentPackageManager,
            StudentEditInfo.name: StudentEditInfo,
        }

    def get_message(self, chat_id=None):
        text = f"{print_user_name(self.user)}\n"
        text += f"{print_student_unseen_conversations(self.user)}\n"
        text += f"{print_student_active_packages(self.user)}"

        _list = [
            [(StudentQuestionManager.text, StudentQuestionManager.name, "")],
            [(StudentPackageManager.text, StudentPackageManager.name, "")],
            [(StudentEditInfo.text, StudentEditInfo.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)

        if not chat_id:
            # self.set_info()
            chat_id = self.chat_id

        message = self._get_message_dict(
            chat_id=chat_id, text=text, inline_keyboard=inline_keyboard
        )

        return message


class StudentBaseState(BaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.home_state = StudentHome

    def _get_home_and_back_inline_button(self, back_state):
        btns = [
            [
                {
                    "text": StudentHome.text,
                    "callback_data": json.dumps(
                        {"state": StudentHome.name, "data": ""}
                    ),
                }
            ],
            [
                {
                    "text": self.BACK_BTN_TEXT,
                    "callback_data": json.dumps({"state": back_state.name, "data": ""}),
                }
            ],
        ]
        return btns


class StudentEditInfo(StudentBaseState):
    name = "STDNT_edit_info"
    text = "ویرایش مشحصات"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentEditInfoName.name: StudentEditInfoName,
            StudentEditInfoPhoneNumber.name: StudentEditInfoPhoneNumber,
            StudentEditInfoGrade.name: StudentEditInfoGrade,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = print_user_detailed(self.user)
        _list = [
            [(StudentEditInfoName.text, StudentEditInfoName.name, "")],
            [(StudentEditInfoPhoneNumber.text, StudentEditInfoPhoneNumber.name, "")],
            [(StudentEditInfoGrade.text, StudentEditInfoGrade.name, "")],
            [(self.BACK_BTN_TEXT, StudentHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message

    def _handle_callback_query(self):
        http_response = super()._handle_callback_query()
        _dict = {
            # "update": self.message_id,
            "delete": self.sent_message_id,
        }
        self.user.userstate.message_ids = json.dumps(_dict)
        self.user.userstate.save()
        return http_response


class StudentBaseEditInfo(StudentBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.parent_state = StudentEditInfo
        self.field_name = ""

    def _handle_message(self):
        new_value = self.input_text
        setattr(self.user, self.field_name, new_value)
        self.user.save()
        _msg_ids = self.user.userstate.message_ids
        _msg_ids = json.loads(_msg_ids)
        # to_update = _msg_ids["update"]
        to_delete = _msg_ids["delete"]

        message = self._get_message_dict(message_id=to_delete)
        self.delete_message(message)

        message = self._get_message_dict(message_id=self.message_id)
        self.delete_message(message)

        message = self.parent_state(self._tlg_res, self.user).get_message()
        self.send_message(message)

        self.user.userstate.state = bot_models.State.objects.get(
            name=self.parent_state.name
        )
        self.user.userstate.save()

        return HttpResponse("ok")


class StudentEditInfoName(StudentBaseEditInfo):
    name = "STDNT_edit_info_name"
    text = "ویرایش نام"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.MESSAGE)
        self.expected_states = {
            StudentEditInfo.name: StudentEditInfo,
            StudentHome.name: StudentHome,
        }
        self.field_name = "name"

    def get_message(self, chat_id=None):
        text = "نام خود را وارد کنید."
        message = self._get_message_dict(text=text, chat_id=chat_id)
        return message


class StudentEditInfoPhoneNumber(StudentBaseEditInfo):
    name = "STDNT_edit_info_phone_number"
    text = "ویرایش شماره تماس"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.MESSAGE)
        self.expected_states = {
            StudentEditInfo.name: StudentEditInfo,
            StudentHome.name: StudentHome,
        }
        self.field_name = "phone_number"

    def get_message(self, chat_id=None):
        text = "شماره تماس خود را وارد کنید."
        message = self._get_message_dict(text=text, chat_id=chat_id)
        return message


class StudentEditInfoGrade(StudentBaseState):
    name = "STDNT_edit_info_grade"
    text = "ویرایش مقطع تحصیلی"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentHome.name: StudentHome,
            StudentEditInfo.name: StudentEditInfo,
        }

    def get_message(self, chat_id=None):
        text = "پایه و رشته تحصیلی حود را انتخاب کنید.\n"
        _list = []
        for f, f_text in eps_models.Subject.FIELD_CHOICES[:-1]:
            row = []
            for g, g_text in eps_models.Subject.GRADE_CHOICES[:-1]:
                btn = (
                    f"{g_text} {f_text}",
                    StudentEditInfo.name,
                    {"grade": f"{g}{f}"},
                )
                row.append(btn)
            _list.append(row)
        l = [(StudentHome.text, StudentHome.name, "")]
        _list.append(l)
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message

    def _handle_callback_query(self):
        if self.callback_query_next_state == StudentHome.name:
            return super()._handle_callback_query()
        # self.logger.error(msg=f"{self.callback_query_data}")
        # TODO handle errors
        self.user.student.grade = self.callback_query_data["grade"]
        self.user.student.save()
        http_response = super()._handle_callback_query()

        return http_response


class StudentPackageManager(StudentBaseState):
    name = "STDNT_package_manager"
    text = "مدیریت بسته"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentNewPackage.name: StudentNewPackage,
            StudentPackageHistory.name: StudentPackageHistory,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = print_student_active_packages(self.user)
        _list = [
            [(StudentNewPackage.text, StudentNewPackage.name, "")],
            [(StudentPackageHistory.text, StudentPackageHistory.name, "")],
            [(self.BACK_BTN_TEXT, StudentHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message


class StudentNewPackage(StudentBaseState):
    name = "STDNT_new_package"
    text = "بسته جدید"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentNewPackageConfirm.name: StudentNewPackageConfirm,
            StudentNewPackageChoose.name: StudentNewPackageChoose,
            StudentPackageManager.name: StudentPackageManager,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = "از لیست زیر یک بسته را انتخاب کنید:\n"

        _list = [
            [
                (
                    "۳۰ سوال بسته جامع تخصصی",
                    StudentNewPackageConfirm.name,
                    {"package": "ALL-SPC-30"},
                )
            ],
            [
                (
                    "۱۰ سوال بسته جامع تخصصی",
                    StudentNewPackageConfirm.name,
                    {"package": "ALL-SPC-10"},
                )
            ],
            [
                (
                    "۳۰ سوال بسته تک درس تخصصی",
                    StudentNewPackageChoose.name,
                    {"package": "ONE-SPC-30"},
                )
            ],
            [
                (
                    "۱۰ سوال بسته تک درس تخصصی",
                    StudentNewPackageChoose.name,
                    {"package": "ONE-SPC-10"},
                )
            ],
            [
                (
                    "۳۰ سوال بسته جامع عمومی",
                    StudentNewPackageConfirm.name,
                    {"package": "ALL-GEN-30"},
                )
            ],
            [
                (
                    "۱۰ سوال بسته جامع عمومی",
                    StudentNewPackageConfirm.name,
                    {"package": "ALL-GEN-10"},
                )
            ],
        ]

        inliine_keyboard = self._get_inline_keyboard_list(_list)
        _home_back = self._get_home_and_back_inline_button(StudentPackageManager)
        inliine_keyboard += _home_back
        message = self._get_message_dict(
            text=text, inline_keyboard=inliine_keyboard, chat_id=chat_id
        )
        return message


class StudentNewPackageChoose(StudentBaseState):
    name = "STDNT_new_package_choose"
    text = "انتخاب تک درس"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentNewPackageConfirm.name: StudentNewPackageConfirm,
            StudentNewPackageChoose.name: StudentNewPackageChoose,
            StudentPackageManager.name: StudentPackageManager,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        pass


class StudentNewPackageConfirm(StudentBaseState):
    name = "STDNT_new_package_confirm"
    text = "تایید حرید"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            "STDNT_package_manager": StudentPackageManager,
            "STDNT_new_package": StudentNewPackage,
            "STDNT_home": StudentHome,
        }

    def get_message(self, chat_id=None):
        try:
            self._set_callback_query_data()
            selected_package = conv_models.Package.objects.get(
                pk=int(self.callback_query_data)
            )
            if selected_package.is_active:
                text = "حرید بسته:\n"
                text += str(selected_package)
                inline_keyboard = [
                    [{"text": "صفحه پرداخت", "url": "https://zarinpal.com"}],
                ]
                _home_back = self._get_home_and_back_inline_button(StudentNewPackage)
                inline_keyboard += _home_back
                message = self._get_message_dict(
                    text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
                )
                return message
        except ObjectDoesNotExist as err:
            msg = self._get_error_prefix()
            msg += f"{self.data}"
            self.logger.error(msg=msg)

        text = "امکان خرید این بسته وجود ندارد."
        inline_keyboard = self._get_home_and_back_inline_button(StudentNewPackage)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message


class StudentPackageHistory(StudentBaseState):
    name = "STDNT_package_history"
    text = "تاریخچه بسته ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            "STDNT_package_manager": StudentPackageManager,
            "STDNT_home": StudentHome,
        }

    def get_message(self, chat_id=None):
        text = f"{self.text}:\n"
        text += print_student_all_packages_detailed(self.user)
        inline_keyboard = self._get_home_and_back_inline_button(StudentPackageManager)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message


class StudentQuestionManager(StudentBaseState):
    name = "STDNT_question_manager"
    text = "مدیریت پرسش و پاسخ"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentNewQuestionChoose.name: StudentNewQuestionChoose,
            StudentQuestionHistory.name: StudentQuestionHistory,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = print_student_unseen_conversations(user=self.user)
        _list = [
            [(StudentNewQuestionChoose.text, StudentNewQuestionChoose.name, "")],
            [(StudentQuestionHistory.text, StudentQuestionHistory.name, "")],
            [(self.BACK_BTN_TEXT, StudentHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message


class StudentNewQuestionChoose(StudentBaseState):
    name = "STDNT_new_question_choose"
    text = "پرسش جدید"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentQuestionManager.name: StudentQuestionManager,
            StudentNewQuestionChoose.name: StudentNewQuestionChoose,
            StudentNewPackage.name: StudentNewPackage,
            StudentNewQuestionCompose.name: StudentNewQuestionCompose,
            StudentHome.name: StudentHome,
        }

    def _get_buttons(self, callback_data=""):
        _list = []
        grade = subject = student_package = ""
        if callback_data == "":
            _list = [
                [
                    (
                        self.user.student.grade.get_grade_display(),
                        StudentNewQuestionChoose.name,
                        {"step": "grade", "grade": self.user.student.grade},
                    )
                ]
            ]
            for f, f_text in eps_models.Subject.FIELD_CHOICES[:-1]:
                row = []
                for g, g_text in eps_models.Subject.GRADE_CHOICES[:-1]:
                    btn = (
                        f"{g_text, f_text}",
                        StudentNewQuestionChoose.name,
                        {"step": "grade", "grade": f"{g}{f}"},
                    )
                    row.append(btn)
                _list.append(row)
            return _list
        else:
            _dict = json.loads(self.callback_query_data)
            step = _dict["step"]
            if step == "grade":
                grade = _dict["grade"]
                g = grade[:2]
                f = grade[2:]
                _list = []
                subjects = eps_models.Subject.objects.filter(field=f, grade=g)
                for s in subjects:
                    l = [
                        (
                            s.name,
                            StudentNewQuestionChoose.name,
                            {"step": "subject", "subject": s.pk, "grade": grade},
                        )
                    ]
                    _list.append(l)
                l = [("اتغییر مقطع", StudentNewQuestionChoose, "")]
                _list.append(l)
                return _list
            elif step == "subject":
                subject = _dict["subject"]
                grade = _dict["grade"]
                student_packages = conv_models.StudentPackage.objects.filter(
                    student__user=self.user, package__subjects__pk=subject
                )
                _list = []
                for p in student_packages:
                    l = [
                        (
                            f"{p.package.name} {p.asked_questions}/{p.package.number_of_questions}",
                            StudentNewQuestionChoose,
                            {
                                "step": "student_package",
                                "student_package": p.pk,
                                "subject": subject,
                                "grade": grade,
                            },
                        )
                    ]
                    _list.append(l)
                l = [
                    (
                        "اتغییر درس",
                        StudentNewQuestionChoose,
                        {"step": "grade", "grade": grade},
                    )
                ]
            elif step == "student_package":
                grade = _dict["grade"]
                subject = _dict["subject"]
                student_package = _dict["student_package"]

                _list = []
                l = [
                    (
                        "تغییر درس",
                        StudentNewQuestionChoose.name,
                        {"step": "subject", "subject": subject, "grade": grade},
                    )
                ]
                _list.append(l)
                l = [
                    (
                        StudentNewQuestionCompose.text,
                        StudentNewQuestionCompose.name,
                        {
                            "grade": grade,
                            "subject": subject,
                            "student_package": student_package,
                        },
                    )
                ]
                _list.append(l)
        return _list, grade, subject, student_package

    def get_message(self, chat_id=None):
        _stdnt_pckgs = conv_models.StudentPackage.objects.filter(
            student__user=self.user, is_done=False
        )
        if _stdnt_pckgs.count() == 0:
            text = "شما بسته فعالی ندارید\n"
            _list = [
                [
                    (StudentNewPackage.text, StudentNewPackage.name, ""),
                ],
            ]
            inline_keyboard = self._get_inline_keyboard_list(_list)
            inline_keyboard += self._get_home_and_back_inline_button(
                StudentQuestionManager
            )
            message = self._get_message_dict(text=text, inline_keyboard=inline_keyboard)
            return message

        if self.callback_query_data == "":
            _dict = ""
        else:
            _dict = json.loads(self.callback_query_data)
        _list, grade, subject, student_package = self._get_buttons(_dict)
        inline_keyboard = self._get_inline_keyboard_list(_list)
        grade = ""
        subject = ""
        student_package = ""
        text = "مقطع تحصیلی، درس و بسته مورد نظر در رابطه با پرسش خود را با استفاده از دکمه های زیر انتخاب کنید.\n"
        text += f"مقطع تحصیلی: {grade}\n"
        text += f"درس: {subject}\n"
        text += f"بسته: {student_package}\n"
        inline_keyboard += self._get_home_and_back_inline_button(StudentQuestionManager)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message

    def _handle_callback_query(self):
        # self.logger.error(f"XXX: {self.callback_query_next_state=}")
        if self.callback_query_next_state == StudentNewQuestionChoose.name:
            data = self._get_message_dict(message_id=self.message_id)
            self.delete_message(data)
            next_message = self.get_message()
            self.send_message(next_message)
            http_respone = HttpResponse()
        elif self.callback_query_next_state == StudentNewQuestionCompose.name:
            data = self._get_message_dict(message_id=self.message_id)
            self.delete_message(data)
            next_message = StudentNewQuestionCompose(
                self._tlg_res, self.user
            ).get_message()
            self.send_message(next_message)
            http_respone = HttpResponse()
            self.user.userstate.state = bot_models.State.objects.get(
                name=StudentNewQuestionCompose.name
            )
            self.user.userstate.save()
        else:
            http_respone = super()._handle_callback_query()
        return http_respone


class StudentNewQuestionCompose(StudentBaseState):
    name = "STDNT_new_question_compose"
    text = "نوشتن پرسش"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.MESSAGE)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentNewQuestionComposeConfirm.name: StudentNewQuestionComposeConfirm,
            StudentNewQuestionChoose.name: StudentNewQuestionChoose,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = "سوال خود بپرسید:\n"
        text += "می توانید سوال خود را به صورت متن، عکس یا ویس ارسال کنید.\n"
        _list = [
            [{StudentHome.text, StudentHome.name, ""}],
            [("تغییر مقطغ، درس یا بسته", StudentNewQuestionChoose.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(text=text, inline_keyboard=inline_keyboard)
        return message


class StudentNewQuestionComposeConfirm(StudentBaseState):
    name = "STDNT_new_question_compose_confirm"
    text = "تایید و ارسال"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentQuestionManager.name: StudentQuestionManager,
            StudentNewQuestionCompose.name: StudentNewQuestionCompose,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = "سوال شما دریافت شد"
        _list = [
            [(self.text, StudentQuestionManager.name, "")],
            [("تغییر پرسش", StudentNewQuestionCompose.name, {"edit": True})],
            [(StudentHome.text, StudentHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message


class StudentQuestionHistory(StudentBaseState):
    name = "STDNT_question_history"
    text = "تاریخچه پرسش ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_states = {
            StudentQuestionDetailed.name: StudentQuestionDetailed,
            StudentQuestionManager.name: StudentQuestionManager,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = print_student_all_conversations(self.user)
        inline_keyboard = self._get_home_and_back_inline_button(StudentQuestionManager)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message


class StudentQuestionDetailed(StudentBaseState):
    name = "STDNT_question_detailed"
    text = "نمایش پرسش و پاسخ"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
