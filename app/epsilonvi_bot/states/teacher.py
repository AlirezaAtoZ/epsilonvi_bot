from django.core.exceptions import ValidationError, NON_FIELD_ERRORS, ObjectDoesNotExist
from django.http import HttpResponse
from epsilonvi_bot import permissions as perm
from epsilonvi_bot import models as eps_models
from epsilonvi_bot.states.base import (
    BaseState,
    MessageTypeMixin,
    ButtonsListMixin,
    EditModelMixin,
    ConversationDetailMixin,
)
from user import models as usr_models
from conversation import models as conv_models
from conversation.handlers import ConversationStateHandler


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


def get_conversation_list_display(conversatoins_query):
    if conversatoins_query.count() == 0:
        return "سوالی وجود ندارد.\n"
    text = ""
    help_dict = {
        "Q-STDNT-COMP": "سوال",
        "RQ-STDNT-COMP": "اعتراض",
        "A-TCHER-COMP": "پاسخ",
        "RA-TCHER-COMP": "پاسح به اعتراض",
    }
    for c in conversatoins_query:
        _text = help_dict.get(c.conversation_state, "UNKNWN")
        l = f"{c.get_telegram_command()} - {c.subject}\n"
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

    def _handle_delete_messages(self):
        # self.logger.error(f"{self.get_message_ids()=}")
        message_ids = self.get_message_ids("delete")
        # self.logger.error(f"{message_ids=}")
        for m_id in message_ids:
            # self.logger.error(f"{m_id=}")
            data = self._get_message_dict(chat_id=self.chat_id, message_id=m_id)
            self.delete_message(data)
        return True

    def send_error(self, target_state, chat_id=None):
        _err_state = TeacherError(self._tlg_res, self.user)
        message = _err_state.get_message(chat_id=chat_id)
        inline_keyboard = self._get_default_buttons(target_state)
        message = self._get_message_dict(**message, inline_keyboard=inline_keyboard)

        trans_method = getattr(self, self.transition_method_name)
        trans_method(message)

        msg = self._get_error_prefix()
        msg += f"{self.user.userstate.state.name}\t"
        msg += f"{self.user=}\t{self.input_text}"
        self.logger.error(msg=msg)

        return HttpResponse()


class TeacherError(BaseState):
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


class TeacherHome(ButtonsListMixin, TeacherBaseState):
    name = "TCHER_home"
    text = "صفحه اصلی"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_states = {
            TeacherInfoManager.name: TeacherInfoManager,
            TeacherQuestionManager.name: TeacherQuestionManager,
        }

    def get_message(self, chat_id=None):
        # self.logger.error(f"get_message")
        text = get_teacher_detailed(self.user.teacher)
        # self.logger.error(f"{text=}")
        states = [
            TeacherQuestionManager,
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


# question manager
class TeacherQuestionBaseState(TeacherBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_states = {
            TeacherHome.name: TeacherHome,
            TeacherQuestionManager.name: TeacherQuestionManager,
            TeacherQuestionSelect.name: TeacherQuestionSelect,
            TeacherQuestionListActive.name: TeacherQuestionListActive,
            TeacherQuestionHistory.name: TeacherQuestionHistory,
            TeacherQuestionDetail.name: TeacherQuestionDetail,
            TeacherQuestionCompose.name: TeacherQuestionCompose,
            TeacherQuestionConfirm.name: TeacherQuestionConfirm,
            TeacherReQuestionCompose.name: TeacherReQuestionCompose,
            TeacherReQuestionConfirm.name: TeacherReQuestionConfirm,
        }
        self.expected_input_types = [self.CALLBACK_QUERY]


class TeacherQuestionManager(ButtonsListMixin, TeacherQuestionBaseState):
    name = "TCHER_question_manage"
    text = "مدیریت سوال ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [self.CALLBACK_QUERY]

    def get_message(self, chat_id=None):
        states_list = [TeacherQuestionSelect, TeacherQuestionListActive]
        message = self.get_state_buttons(
            state_obj=self,
            states_list=states_list,
            chat_id=chat_id,
            home_state=TeacherHome,
        )
        return message


class TeacherQuestionSelect(TeacherQuestionBaseState):
    name = "TCHER_question_select"
    text = "انتخاب سوال"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None, selected_field=None):
        text = ""
        _list = []
        help_dict = {
            "MTH": "ریاضی",
            "BIO": "زیست",
            "ECO": "انسانی",
            "GEN": "عمومی",
        }
        # global queries
        ## teacher fields
        _fields = self.user.teacher.subjects.filter(is_active=True)
        fields = _fields.values("field").distinct()
        ## select or default field
        if not selected_field:
            _f = fields.first()
            selected_field = _f["field"] if _f else ""
        ## available conversations by field
        _f = _fields.filter(field=selected_field)
        conversations = conv_models.Conversation.objects.filter(
            subject__in=_f, conversation_state="Q-ADMIN-APPR"
        )

        # create field row btns
        row_field_btns = []
        for field in fields:
            f = field.get("field")
            selected = f"✅" if f == selected_field else ""
            btn = [
                f"{selected} {help_dict.get(f)}",
                TeacherQuestionSelect.name,
                {"field": f},
            ]
            row_field_btns.append(btn)
        _list.append(row_field_btns)

        text += f"لیست سوالات مربوط به رشته {help_dict.get(selected_field)}:\n"

        # available convesations list
        for i, c in enumerate(conversations):
            text += f"{i+1} - {c.get_telegram_command()} {c.subject}\n"
        inline_btns = self._get_inline_keyboard_list(_list)
        inline_btns += self._get_default_buttons(TeacherQuestionManager)
        message = self._get_message_dict(
            chat_id=chat_id, text=text, inline_keyboard=inline_btns
        )
        return message

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        field = self.callback_query_data.get("field", None)
        if field and self.callback_query_next_state == TeacherQuestionSelect.name:
            get_message_kwargs = {"selected_field": field}
        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class TeacherQuestionListActive(TeacherQuestionBaseState):
    name = "TCHER_question_list_active"
    text = "سوال های فعال"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None):
        text = "مکالمات فعال\n"
        convs = conv_models.Conversation.objects.filter(
            teacher=self.user.teacher, is_done=False
        )
        text += get_conversation_list_display(convs)
        inline_btns = self._get_default_buttons(TeacherQuestionManager)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_btns, chat_id=chat_id
        )
        return message


class TeacherQuestionHistory(TeacherQuestionBaseState):
    name = "TCHER_question_history"
    text = "تاریخچه سوال ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)


class TeacherQuestionDetail(ConversationDetailMixin, TeacherQuestionBaseState):
    name = "TCHER_question_detail"
    text = "جزییات سوال"

    APPROVE_BUTTON = "پاسخ به این سوال"
    CONFIRM_BUTTON = "تایید"
    DENY_BUTTON = "رد"

    TEACHER_REWRITE_TEXT = "پاسخ مجدد"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, conversation, confirm=False, chat_id=None):
        _list = []
        _ch = ConversationStateHandler(conversation)
        if _ch.is_waiting_on_teacher():
            if conversation.teacher == self.user.teacher:
                re_write_btn = [
                    self.TEACHER_REWRITE_TEXT,
                    TeacherReQuestionCompose.name,
                    {"c_id": conversation.pk},
                ]
                _list.append([re_write_btn])
            else:
                # first select the question
                select_btn = [
                    self.APPROVE_BUTTON,
                    TeacherQuestionDetail.name,
                    {"c_id": conversation.pk, "action": "appr"},
                ]
                # then confirm the question
                confirm_btn = [
                    self.CONFIRM_BUTTON,
                    TeacherQuestionCompose.name,
                    {"c_id": conversation.pk, "action": "cnfrm"},
                ]
                _list.append([confirm_btn]) if confirm else _list.append([select_btn])
        # add home and back button
        inline_btns = self._get_inline_keyboard_list(_list)
        inline_btns += self._get_default_buttons(TeacherQuestionSelect)
        # last message text
        text = "عملیات ها:\n"
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_btns, chat_id=chat_id
        )
        return message

    def get_messages(
        self, conversation: conv_models.Conversation, chat_id, confirm=False
    ):
        messages = self._get_conversation_messages(
            conversation=conversation, state_object=self, chat_id=chat_id
        )
        message = self.get_message(conversation, confirm, chat_id)
        # add last message to messages list
        messages.append({"message_type": "text", "message": message})
        return messages

    def _handle_send_messages(self, conversation):
        messages = self.get_messages(conversation, self.chat_id)
        ids = []
        for m in messages:
            message_type = m.get("message_type")
            message = m.get("message")
            method = getattr(self, f"send_{message_type}", self.send_unkown)
            _m_id = method(message)
            ids.append(_m_id)
        self.save_message_ids(delete_ids=ids)
        self._set_user_state(TeacherQuestionDetail)

        return HttpResponse("ok")

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        action = self.callback_query_data.get("action", None)
        cid = self.callback_query_data.get("c_id", None)
        if (
            action
            and cid
            and self.callback_query_next_state == TeacherQuestionDetail.name
        ):
            conversation = conv_models.Conversation.objects.filter(pk=cid).first()
            if conversation:
                if not conversation.teacher == None:
                    # this conversations already have a teacher
                    pass
                elif action == "appr":
                    # button changes to confirm
                    get_message_kwargs = {"conversation": conversation, "confirm": True}
                else:
                    # action not known
                    pass
        elif (
            action
            and cid
            and self.callback_query_next_state == TeacherQuestionCompose.name
        ):
            conversation = conv_models.Conversation.objects.filter(pk=cid).first()
            if conversation and action == "cnfrm":
                _conv_hand = ConversationStateHandler(conversation)
                _conv_hand.handle()  # Q-ADMIN-APPR -> A-TCHER-DRFT
                conversation.teacher = self.user.teacher
                conversation.save()
                # self._handle_delete_messages()
        elif cid and self.callback_query_next_state == TeacherReQuestionCompose.name:
            conversation = conv_models.Conversation.objects.filter(pk=cid).first()
            if conversation:
                _conv_hand = ConversationStateHandler(conversation)
                _conv_hand.handle()  # RQ-ADMIN-APPR -> RA-TCHER-DRFT

        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class TeacherQuestionCompose(MessageTypeMixin, TeacherQuestionBaseState):
    name = "TCHER_question_compose"
    text = "نوشتن پاسخ"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [self.MESSAGE, self.CALLBACK_QUERY]

    def get_message(self, chat_id=None):
        text = "پاسخ این سوال را ارسال کنید.\n شما می توانید پاسخ خود را به صورت متن، تصویر یا ویس بفرستید.\n"
        message = self._get_message_dict(text=text, chat_id=chat_id)
        return message

    def _handle_base_type(self, user, message_model, conversation_id=None):
        try:
            if conversation_id:
                conversation = conv_models.Conversation.objects.get(pk=conversation_id)
                conversation.answer.all().delete()
            else:
                conversation = conv_models.Conversation.objects.get(
                    teacher=user.teacher, conversation_state="A-TCHER-DRFT"
                )
        except ObjectDoesNotExist as err:
            return None
        else:
            conversation.answer.all().delete()
            conversation.answer.add(message_model)
            conversation.save()
            return conversation

    def _handle_other_type(self):
        return HttpResponse()

    def _handle_text_type(self):
        return super()._handle_text_type(
            self.message_id, self.chat_id, self.user, self.input_text
        )

    def _handle_photo_type(self):
        return super()._handle_photo_type(
            self.data, self.message_id, self.chat_id, self.user
        )

    def _handle_voice_type(self):
        return super()._handle_voice_type(
            self.data, self.message_id, self.chat_id, self.user
        )

    def _handle_message(self):
        message_type = self._get_message_type(self.data)
        _handle_method = getattr(self, f"_handle_{message_type}_type")
        conversation = _handle_method()
        if not conversation:
            self.send_error(TeacherQuestionManager, chat_id=self.chat_id)

        next_state = TeacherQuestionConfirm(self._tlg_res, self.user)
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

        self._set_user_state(TeacherQuestionConfirm)

        return HttpResponse()


class TeacherQuestionConfirm(TeacherQuestionBaseState):
    name = "TCHER_question_confirm"
    text = "تایید و ارسال"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, conversation, chat_id=None):
        # self.logger.error(f"{_c} {kwargs}")
        data = conversation.answer.all().first().get_message_dict()
        _list = [
            [
                (
                    self.text,
                    TeacherQuestionManager.name,
                    {"conversation": conversation.pk},
                )
            ],
            [("تغییر پاسخ", TeacherQuestionCompose.name, "")],
            [(TeacherHome.text, TeacherHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            chat_id=chat_id, inline_keyboard=inline_keyboard, **data
        )

        return message

    def _handle_callback_query(self):
        _conv_id = self.callback_query_data.get("conversation", None)
        if _conv_id and self.callback_query_next_state == TeacherQuestionManager.name:
            conversation = conv_models.Conversation.objects.filter(
                pk=_conv_id, teacher=self.user.teacher
            ).first()
            if conversation:
                _conv_hand = ConversationStateHandler(conversation)
                _conv_hand.handle()  # A-TCHER-DRFT -> A-TCHER-COMP
            else:
                text = "پرسش و پاسخ مورد نظر پیدا نشد."
                message = self._get_message_dict(text=text, chat_id=self.chat_id)
                self.transition(message=message)
                msg = self._get_error_prefix()
                msg += f"{self.user=}\t{_conv_id}"
                self.logger.error(msg=msg)

        return super()._handle_callback_query()


class TeacherReQuestionCompose(MessageTypeMixin, TeacherQuestionBaseState):
    name = "TCHER_re_question_compose"
    text = "نوشتن پاسخ"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [self.MESSAGE, self.CALLBACK_QUERY]

    def get_message(self, chat_id=None):
        text = "پاسخ این سوال را ارسال کنید.\n شما می توانید پاسخ خود را به صورت متن، تصویر یا ویس بفرستید.\n"
        message = self._get_message_dict(text=text, chat_id=chat_id)
        return message

    def _handle_base_type(self, user, message_model, conversation_id=None):
        try:
            if conversation_id:
                conversation = conv_models.Conversation.objects.get(pk=conversation_id)
                conversation.re_answer.all().delete()
            else:
                conversation = conv_models.Conversation.objects.get(
                    teacher=user.teacher, conversation_state="RA-TCHER-DRFT"
                )
        except ObjectDoesNotExist as err:
            return None
        else:
            conversation = conv_models.Conversation.objects.filter(teacher=self.user.t)
            conversation.re_answer.all().delete()
            conversation.re_answer.add(message_model)
            conversation.save()
            return conversation

    def _handle_other_type(self):
        return HttpResponse()

    def _handle_text_type(self):
        return super()._handle_text_type(
            self.message_id, self.chat_id, self.user, self.input_text
        )

    def _handle_photo_type(self):
        return super()._handle_photo_type(
            self.data, self.message_id, self.chat_id, self.user
        )

    def _handle_voice_type(self):
        return super()._handle_voice_type(
            self.data, self.message_id, self.chat_id, self.user
        )

    def _handle_message(self):
        message_type = self._get_message_type(self.data)
        _handle_method = getattr(self, f"_handle_{message_type}_type")
        conversation = _handle_method()
        if not conversation:
            self.send_error(TeacherQuestionManager, chat_id=self.chat_id)

        next_state = TeacherReQuestionConfirm(self._tlg_res, self.user)
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

        self._set_user_state(TeacherReQuestionConfirm)

        return HttpResponse()


class TeacherReQuestionConfirm(TeacherQuestionBaseState):
    name = "TCHER_re_question_confirm"
    text = "تایید و ارسال"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, conversation, chat_id=None):
        # self.logger.error(f"{_c} {kwargs}")
        data = conversation.re_answer.all().first().get_message_dict()
        _list = [
            [
                (
                    self.text,
                    TeacherQuestionManager.name,
                    {"conversation": conversation.pk},
                )
            ],
            [("تغییر پاسخ", TeacherQuestionCompose.name, "")],
            [(TeacherHome.text, TeacherHome.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            chat_id=chat_id, inline_keyboard=inline_keyboard, **data
        )

        return message

    def _handle_callback_query(self):
        _conv_id = self.callback_query_data.get("conversation", None)
        if _conv_id and self.callback_query_next_state == TeacherQuestionManager.name:
            conversation = conv_models.Conversation.objects.filter(
                pk=_conv_id, teacher=self.user.teacher
            ).first()
            if conversation:
                _conv_hand = ConversationStateHandler(conversation)
                _conv_hand.handle()  # RA-TCHER-DRFT -> RA-TCHER-COMP
            else:
                text = "پرسش و پاسخ مورد نظر پیدا نشد."
                message = self._get_message_dict(text=text, chat_id=self.chat_id)
                self.transition(message=message)
                msg = self._get_error_prefix()
                msg += f"{self.user=}\t{_conv_id}"
                self.logger.error(msg=msg)

        return super()._handle_callback_query()
