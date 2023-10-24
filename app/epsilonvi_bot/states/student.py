import copy
import json

from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from .base import BaseState
from conversation import models as conv_models
from conversation import handlers
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
        student__user=user,
        is_done=False,
        is_pending=False,
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
        t = f"{idx}- {conv.get_telegram_command()}\n"
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
            t = f"{idx}- {conv.get_telegram_command()} {status} {conv.subject}\n"
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

    def get_message(self, chat_id=None):
        text = "مشکلی پیش آمده مجددا تلاش کنید."
        message = self._get_message_dict(text=text, chat_id=chat_id)
        return message

    def _handle_message(self):
        self.send_text(self.get_message(self.chat_id))
        return HttpResponse("Something went wrong")

    def _handle_callback_query(self):
        self.send_text(self.get_message(self.chat_id))
        return HttpResponse("Something went wrong")


class StudentHome(BaseState):
    name = "STDNT_home"
    text = "صفحه اصلی"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        # self.expected_input_types.append(self.MESSAGE)

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

    def send_error(self, target_state, chat_id=None):
        _err_state = StudentError(self._tlg_res, self.user)
        message = _err_state.get_message(chat_id=chat_id)
        inline_keyboard = self._get_home_and_back_inline_button(target_state)
        message = self._get_message_dict(**message, inline_keyboard=inline_keyboard)

        trans_method = getattr(self, self.transition_method_name)
        trans_method(message)

        msg = self._get_error_prefix()
        msg += f"{self.user.userstate.state.name}\t"
        msg += f"{self.user=}\t{self.input_text}"
        self.logger.error(msg=msg)

        return HttpResponse()


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
        self.send_text(message)

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


class StudentPackageBaseState(StudentBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_states = {
            StudentHome.name: StudentHome,
            StudentPackageManager.name: StudentPackageManager,
            StudentPackageConfirm.name: StudentPackageConfirm,
            StudentPackageAdd.name: StudentPackageAdd,
        }
        self.expected_input_types = [self.CALLBACK_QUERY]


class StudentPackageManager(StudentBaseState):
    name = "STDNT_package_manager"
    text = "مدیریت بسته"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentPackageAdd.name: StudentPackageAdd,
            StudentPackageAdd.name: StudentPackageAdd,
            StudentPackageHistory.name: StudentPackageHistory,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = print_student_active_packages(self.user)
        _list = [
            [(StudentPackageAdd.text, StudentPackageAdd.name, "")],
            [(StudentPackageHistory.text, StudentPackageHistory.name, "")],
            [(self.BACK_BTN_TEXT, StudentHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message


class StudentPackageAdd(StudentPackageBaseState):
    name = "STDNT_package_add"
    text = "خرید بسته جدید"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(
        self,
        field=None,
        number_of_questions=None,
        single=False,
        chat_id=None,
    ):
        text = "با استفاده از دکمه های زیر یک بسته انتخاب کنید.\n"

        field = field if field else self.user.student.grade[2:]
        num_que = number_of_questions if number_of_questions else 10
        data = {"noq": num_que, "field": field, "single": single}
        _list = []
        # default package

        # number of questions
        char_10q = "✅" if num_que == 10 else ""
        char_30q = "✅" if num_que == 30 else ""

        _d = copy.deepcopy(data)
        _d.update({"noq": 10})
        btn_10q = [f"{char_10q} ۱۰ سوال", StudentPackageAdd.name, _d]

        _d = copy.deepcopy(data)
        _d.update({"noq": 30})
        btn_30q = [f"{char_30q} ۳۰ سوال", StudentPackageAdd.name, _d]

        _list.append([btn_10q, btn_30q])
        # field
        char_mth = "✅" if field == "MTH" else ""
        char_bio = "✅" if field == "BIO" else ""
        char_eco = "✅" if field == "ECO" else ""

        _d = copy.deepcopy(data)
        _d.update({"field": "MTH"})
        btn_mth = [f"{char_mth} ریاضی", StudentPackageAdd.name, _d]

        _d = copy.deepcopy(data)
        _d.update({"field": "BIO"})
        btn_bio = [f"{char_bio} تجربی", StudentPackageAdd.name, _d]

        _d = copy.deepcopy(data)
        _d.update({"field": "ECO"})
        btn_eco = [f"{char_eco} انسانی", StudentPackageAdd.name, _d]

        _list.append([btn_mth, btn_bio, btn_eco])
        # complete packages
        _q1 = conv_models.Package.objects.filter(
            field=field,
            package_type="ALL",
            number_of_questions=num_que,
            is_active=True,
        )
        _q2 = conv_models.Package.objects.filter(
            field="GEN",
            package_type="ALL",
            number_of_questions=num_que,
            is_active=True,
        )
        _q = _q1.union(_q2)
        for p in _q:
            btn = [f"{p}", StudentPackageConfirm.name, {"package": p.pk}]
            _list.append([btn])
        # single packages
        if single:
            _d = copy.deepcopy(data)
            _d.update({"single": False})
            btn_sng = [f"🔽 بسته های تک درس 🔽", StudentPackageAdd.name, _d]
            _list.append([btn_sng])
            _q = conv_models.Package.objects.filter(
                field=field,
                number_of_questions=num_que,
                package_type="SNG",
                is_active=True,
            )
            for p in _q:
                btn = [f"- {p} -", StudentPackageConfirm.name, {"package": p.pk}]
                _list.append([btn])
        else:
            _d = copy.deepcopy(data)
            _d.update({"single": True})
            btn_sng = [f"⏹️ بسته های تک درس ⏹️", StudentPackageAdd.name, _d]
            _list.append([btn_sng])

        btn_home = [f"{StudentHome.text}", StudentHome.name, ""]
        _list.append([btn_home])
        btn_back = [f"{self.BACK_BTN_TEXT}", StudentPackageManager.name, ""]
        _list.append([btn_back])
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        if self.callback_query_next_state == StudentPackageConfirm.name:
            _pid = self.callback_query_data.get("package", None)
            if _pid:
                _q = conv_models.Package.objects.filter(pk=_pid)
                if _q.exists():
                    package = _q[0]
                    get_message_kwargs = {"package": package}
        elif self.callback_query_next_state == StudentPackageAdd.name:
            single = self.callback_query_data.get("single", None)
            field = self.callback_query_data.get("field", None)
            num_que = self.callback_query_data.get("noq", None)
            if num_que and field and not (single is None):
                get_message_kwargs = {
                    "single": single,
                    "field": field,
                    "number_of_questions": num_que,
                }

        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class StudentPackageConfirm(StudentPackageBaseState):
    name = "STDNT_package_confirm"
    text = "تایید و صفحه پرداخت"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, package, chat_id=None):
        text = "خرید پکیج:\n"
        text += f"{package.display_detailed()}"
        inline_keyboard = [
            [
                {
                    "text": "انتقال به درگاه پرداخت",
                    "url": "https://t.me/epsilonvibot?start=action_hello_world",
                }
            ],
        ]
        inline_keyboard += self._get_home_and_back_inline_button(StudentPackageAdd)
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


class StudentQuestionBaseState(StudentBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_states = {
            StudentHome.name: StudentHome,
            StudentQuestionManager.name: StudentQuestionManager,
            StudentQuestionAdd.name: StudentQuestionAdd,
            StudentQuestionCompose.name: StudentQuestionCompose,
        }


class StudentQuestionManager(StudentBaseState):
    name = "STDNT_question_manager"
    text = "مدیریت پرسش و پاسخ"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentQuestionAdd.name: StudentQuestionAdd,
            StudentNewQuestionChoose.name: StudentNewQuestionChoose,
            StudentQuestionHistory.name: StudentQuestionHistory,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        text = print_student_unseen_conversations(user=self.user)
        _list = [
            [(StudentQuestionAdd.text, StudentQuestionAdd.name, "")],
            [(StudentQuestionHistory.text, StudentQuestionHistory.name, "")],
            [(self.BACK_BTN_TEXT, StudentHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message


class StudentQuestionAdd(StudentQuestionBaseState):
    name = "STDNT_question_add"
    text = "پرسش جدید"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [self.CALLBACK_QUERY]

    def get_message(self, student_package=None, chat_id=None):
        text = "درس مورد نظر خود را انتخاب کنید.\n"
        _list = []
        # active packages
        _q = conv_models.StudentPackage.objects.filter(
            student=self.user.student,
            is_done=False,
        )
        for sp in _q:
            char_sel = "⏹️"
            if student_package == sp:
                char_sel = "🔽"
            btn = [
                f"{char_sel} {sp.package} ({sp.asked_questions}/{sp.package.number_of_questions}) {char_sel}",
                StudentQuestionAdd.name,
                {"sp": sp.pk},
            ]
            _list.append([btn])
            if student_package == sp:
                _sp_subjs = sp.package.subjects.all()
                _sp_subjs_len = _sp_subjs.count()
                for i in range(0, _sp_subjs_len, 2):
                    sub = _sp_subjs[i]
                    btn1 = [
                        f"-{sub}-",
                        StudentQuestionCompose.name,
                        {"sp": sp.pk, "s": sub.pk},
                    ]
                    if i + 1 < _sp_subjs_len:
                        sub = _sp_subjs[i + 1]
                        btn2 = [
                            f"-{sub}-",
                            StudentQuestionCompose.name,
                            {"sp": sp.pk, "s": sub.pk},
                        ]
                        _list.append([btn1, btn2])
                    else:
                        _list.append([btn1])

        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_home_and_back_inline_button(StudentQuestionManager)
        message = self._get_message_dict(text=text, inline_keyboard=inline_keyboard)
        return message

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        if self.callback_query_next_state == StudentQuestionAdd.name:
            _spid = self.callback_query_data.get("sp", None)
            if _spid:
                _q = conv_models.StudentPackage.objects.filter(
                    pk=_spid, student=self.user.student
                )
                if _q.exists():
                    student_package = _q[0]
                    get_message_kwargs = {"student_package": student_package}
        elif self.callback_query_next_state == StudentQuestionCompose.name:
            _spid = self.callback_query_data.get("sp", None)
            _subid = self.callback_query_data.get("s", None)
            if _spid and _subid:
                _sp = conv_models.StudentPackage.objects.filter(
                    pk=_spid,
                    student=self.user.student,
                    is_done=False,
                )
                if _sp.exists():
                    student_package = _sp[0]
                    _s = student_package.package.subjects.filter(pk=_subid)
                    if _s.exists():
                        subject = _s[0]
                        _c = conv_models.Conversation.objects.filter(
                            student=self.user.student, conversation_state="ZERO"
                        )
                        _c.delete()
                        _ = conv_models.Conversation.objects.create(
                            student_package=student_package,
                            subject=subject,
                            student=self.user.student,
                        )

        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class StudentNewQuestionChoose(StudentBaseState):
    name = "STDNT_new_question_choose"
    text = "پرسش جدید"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            StudentQuestionManager.name: StudentQuestionManager,
            StudentNewQuestionChoose.name: StudentNewQuestionChoose,
            StudentQuestionCompose.name: StudentQuestionCompose,
            StudentPackageAdd.name: StudentPackageAdd,
            StudentHome.name: StudentHome,
        }

    def get_message(self, chat_id=None):
        student_packages = conv_models.StudentPackage.objects.filter(
            student__user=self.user,
            is_done=False,
            is_pending=False,
        )
        if not student_packages.exists():
            return self._get_message_dict(text="None")
        else:
            text = "یک درس را انتخاب کنید."
            _c = 0
            _r = 0
            _list = [[]]
            # TODO add paging
            for sp in student_packages:
                subjects = sp.package.subjects.all()
                for s in subjects:
                    btn = (
                        f"{s.name} {sp.package.name}",
                        StudentQuestionCompose.name,
                        {"student_package": sp.pk, "subject": s.pk},
                    )
                    if _c >= 3:
                        _c = 1
                        _r += 1
                        _list.append([])
                        _list[_r].append(btn)
                    else:
                        _c += 1
                        _list[_r].append(btn)
            btn = [(f"{StudentPackageAdd.text}", StudentPackageAdd.name, "")]
            _list.append(btn)
            inline_keyboard = self._get_inline_keyboard_list(_list)
            _hbi = self._get_home_and_back_inline_button(StudentQuestionManager)
            inline_keyboard += _hbi
            message = self._get_message_dict(
                text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
            )
            return message

    def _delete_create_draft_conversation(self, student_package_id, subject_id):
        conv_models.Conversation.objects.filter(
            conversation_state="Q-STDNT-DRFT",
            student=self.user.student,
        ).delete()

        _sp = conv_models.StudentPackage.objects.filter(
            pk=student_package_id,
            student__user=self.user,
        )
        if not _sp.exists():
            return False
        _s = _sp[0].package.subjects.filter(pk=subject_id)
        if not _s.exists():
            return False
        conv_models.Conversation.objects.create(
            conversation_state="Q-STDNT-DRFT",
            student=self.user.student,
            student_package=_sp[0],
            subject=_s[0],
        )
        return True

    def _handle_callback_query(self):
        if self.callback_query_next_state == StudentQuestionCompose.name:
            sp_id = self.callback_query_data.get("student_package")
            s_id = self.callback_query_data.get("subject")
            _conv = self._delete_create_draft_conversation(
                student_package_id=sp_id, subject_id=s_id
            )
            if _conv:
                self.save_message_ids(update_ids=[self.message_id])
        return super()._handle_callback_query()


class StudentQuestionCompose(StudentQuestionBaseState):
    name = "STDNT_question_compose"
    text = "نوشتن پرسش"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [self.MESSAGE, self.CALLBACK_QUERY]

    def get_message(self, chat_id=None):
        text = "سوال خود بپرسید:\n"
        text += "می توانید سوال خود را به صورت متن، عکس یا ویس (حداکثر ۶۰ ثانیه) ارسال کنید.\n"
        _list = [
            [{f"{StudentHome.text}", StudentHome.name, ""}],
            [("تغییر مقطع درس یا بسته", StudentQuestionAdd.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message

    def _get_message_type(self, message):
        if type(message) != dict:
            return False
        if "text" in message.keys():
            return "text"
        elif "voice" in message.keys():
            return "voice"
        elif "photo" in message.keys():
            return "photo"
        else:
            # not supported types
            return "other"

    def _handle_other_type(self):
        return HttpResponse()

    def _handle_base_type(self, message_model):
        try:
            conversation = conv_models.Conversation.objects.get(
                student=self.user.student, conversation_state="ZERO"
            )
        except ObjectDoesNotExist as err:
            return None
        else:
            conversation.question.add(message_model)
            conversation.save()
            return conversation

    def _handle_text_type(self):
        _m = bot_models.Message.objects.create(
            message_id=self.message_id,
            chat_id=self.chat_id,
            from_id=self.user,
            text=self.input_text,
            message_type="TXT",
        )
        return self._handle_base_type(message_model=_m)

    def _handle_photo_type(self):
        photo = self.data.get("photo", None)[-1]
        file = bot_models.File.objects.create(
            file_id=photo.get("file_id"),
            file_unique_id=photo.get("file_unique_id"),
            file_type="PHO",
        )
        _m_dict = {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "from_id": self.user,
            "message_type": "PHO",
        }
        caption = self.data.get("caption", None)
        if caption:
            _m_dict.update({"caption": caption})

        _m = bot_models.Message.objects.create(**_m_dict)
        _m.files.add(file)
        _m.save()

        return self._handle_base_type(message_model=_m)

    def _handle_voice_type(self):
        voice = self.data.get("voice", None)
        file = bot_models.File.objects.create(
            file_id=voice.get("file_id"),
            file_unique_id=voice.get("file_unique_id"),
            file_type="VOC",
            duration=voice.get("duration"),
        )
        _m_dict = {
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "from_id": self.user,
            "message_type": "VOC",
        }
        caption = self.data.get("caption", None)
        if caption:
            _m_dict.update({"caption": caption})

        _m = bot_models.Message.objects.create(**_m_dict)
        _m.files.add(file)
        _m.save()

        return self._handle_base_type(message_model=_m)

    def _handle_message(self):
        message_type = self._get_message_type(self.data)
        _handle_method = getattr(self, f"_handle_{message_type}_type")
        conversation = _handle_method()
        if not conversation:
            self.send_error(StudentQuestionManager, chat_id=self.chat_id)

        next_state = StudentQuestionConfirm(self._tlg_res, self.user)
        next_message = next_state.get_message(conversation=conversation)

        if message_type == "text":
            self.send_text(next_message)
        elif message_type == "voice":
            self.send_voice(next_message)
        elif message_type == "photo":
            self.send_photo(next_message)
        else:
            pass

        data = self._get_message_dict(chat_id=self.chat_id, message_id=self.message_id)
        self.delete_message(data)

        self._set_user_state(StudentQuestionConfirm)

        return HttpResponse()


class StudentQuestionConfirm(StudentQuestionBaseState):
    name = "STDNT_question_confirm"
    text = "تایید و ارسال"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [self.CALLBACK_QUERY]
        self.transition_method_name = self.TRANSITION_DEL_SEND

    def get_message(self, conversation, chat_id=None):
        # self.logger.error(f"{_c} {kwargs}")
        data = conversation.question.all()[0].get_message_dict()
        _list = [
            [
                (
                    self.text,
                    StudentQuestionManager.name,
                    {"conversation": conversation.pk},
                )
            ],
            [("تغییر پرسش", StudentQuestionCompose.name, "")],
            [(StudentHome.text, StudentHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            chat_id=chat_id, inline_keyboard=inline_keyboard, **data
        )

        return message

    def _handle_callback_query(self):
        _conv_id = self.callback_query_data.get("conversation", None)
        if _conv_id and self.callback_query_next_state == StudentQuestionManager.name:
            try:
                conversation = conv_models.Conversation.objects.get(
                    student__user=self.user, pk=_conv_id
                )
            except ObjectDoesNotExist as err:
                text = "پرسش و پاسخ مورد نظر پیدا نشد."
                message = self._get_message_dict(text=text, chat_id=self.chat_id)
                self.transition(message=message)
                msg = self._get_error_prefix()
                msg += f"{self.user=}\t{_conv_id}"
                self.logger.error(msg=msg)
                return super()._handle_callback_query()
            else:
                _h = handlers.ConversationHandler(conversation)
                _h.handle()

                return HttpResponse("ok")

        return super()._handle_callback_query()


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
        self.expected_input_types.append(self.CALLBACK_QUERY)

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
