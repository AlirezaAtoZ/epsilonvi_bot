from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.http import HttpResponse
from epsilonvi_bot import permissions as perm
from epsilonvi_bot import models as eps_models
from epsilonvi_bot.states.base import (
    BaseState,
    MessageMixin,
    ButtonsListMixin,
    EditModelMixin,
)
from user import models as usr_models
from conversation import models as conv_models


# TODO check for text input type


def get_teacher_detailed(teacher):
    text = f"{teacher.user.name}\n"
    text += f"پرسش و پاسخ خوانده نشده:\n"
    _q = conv_models.Conversation.objects.filter(
        teacher=teacher, conversation_state__endswith="TCHER"
    )
    for idx, c in enumerate(_q):
        l = f"{idx+1} - {c.get_telegram_command} {c.subject}\n"
        text += l
    return text


class TeacherBaseState(BaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.permissions = [perm.IsTeacher]
        self.expected_input_types = [self.CALLBACK_QUERY]

    def _has_permission(self):
        for _perm in self.permissions:
            permission = _perm()
            if not permission.has_permission(self.user):
                return False
        return True

    def _get_default_buttons(self, back_button_state=None):
        _list = []
        _list.append([(TeacherHome.text, TeacherHome.name, "")])
        # if back_button_state and isinstance(back_button_state, BaseState):
        #     _list.append([(self.BACK_BTN_TEXT, back_button_state.name, "")])
        if back_button_state:
            _list.append([(self.BACK_BTN_TEXT, back_button_state.name, "")])
        btns = self._get_inline_keyboard_list(_list)
        return btns


class TeacherHome(ButtonsListMixin, TeacherBaseState):
    name = "TCHER_home"
    text = "صفحه اصلی"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_states = {
            TeacherInfoManager.name: TeacherInfoManager,
        }

    def get_message(self, chat_id=None):
        # self.logger.error(f"get_message")
        text = get_teacher_detailed(self.user.teacher)
        # self.logger.error(f"{text=}")
        states = [
            TeacherInfoManager,
        ]
        message = self.get_state_buttons(
            state_obj=self,
            states_list=states,
            chat_id=chat_id,
            text=text,
        )
        # self.logger.error(f"{message=}")
        return message


class TeacherInfoBaseState(TeacherBaseState):
    text_2 = ""

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [self.CALLBACK_QUERY]
        self.expected_states = {
            TeacherHome.name: TeacherHome,
            TeacherInfoManager.name: TeacherInfoManager,
            TeacherInfoName.name: TeacherInfoName,
            TeacherInfoCreditCard.name: TeacherInfoCreditCard,
            TeacherInfoPhoneNumber.name: TeacherInfoPhoneNumber,
        }

    def get_message(self, chat_id=None):
        text = f"{self.text_2} خود را وارد کنید"
        inline_keyboard = self._get_default_buttons(TeacherInfoManager)
        message = self._get_message_dict(
            text=text, chat_id=chat_id, inline_keyboard=inline_keyboard
        )
        return message


class TeacherInfoManager(ButtonsListMixin, TeacherInfoBaseState):
    name = "TCHER_info_manager"
    text = "ویرایش مشخصات"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None):
        text = f"نام: {self.user.name}\n"
        text += f"شماره تماس: {self.user.phone_number}\n"
        text += f"شماره کارت: {self.user.teacher.credit_card_number}\n"
        text += f"درس ها:\n"
        for s in self.user.teacher.subjects.all():
            l = f"- {s.name}"
            text += l
        states = [TeacherInfoName, TeacherInfoPhoneNumber, TeacherInfoCreditCard]
        message = self.get_state_buttons(
            state_obj=self,
            states_list=states,
            chat_id=chat_id,
            text=text,
            home_state=TeacherHome,
        )
        return message

    def _handle_callback_query(self):
        if not self.callback_query_next_state == TeacherHome.name:
            self.save_message_ids(
                update_ids=[
                    self.message_id,
                ]
            )
        return super()._handle_callback_query()


class TeacherInfoName(EditModelMixin, TeacherInfoBaseState):
    name = "TCHER_info_name"
    text = "ویرایش نام"
    text_2 = "نام"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types += [self.MESSAGE]

    def _handle_message(self):
        http_response = self.get_text_and_save(
            state_obj=self,
            model=self.user,
            model_field="name",
            next_state_cls=TeacherInfoManager,
            exclude="password",
        )
        return http_response


class TeacherInfoCreditCard(EditModelMixin, TeacherInfoBaseState):
    name = "TCHER_info_credit_card"
    text = "ویرایش شماره کارت"
    text_2 = "شماره کارت"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types += [self.MESSAGE]

    def _handle_message(self):
        http_response = self.get_text_and_save(
            state_obj=self,
            model=self.user.teacher,
            model_field="credit_card_number",
            next_state_cls=TeacherInfoManager,
        )
        return http_response


class TeacherInfoPhoneNumber(EditModelMixin, TeacherInfoBaseState):
    name = "TCHER_info_phone_numbre"
    text = "ویرایش شماره تماس"
    text_2 = "شماره تماس"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types += [self.MESSAGE]

    def _handle_message(self):
        http_response = self.get_text_and_save(
            state_obj=self,
            model=self.user,
            model_field="phone_number",
            next_state_cls=TeacherInfoManager,
            exclude="password",
        )
        return http_response
