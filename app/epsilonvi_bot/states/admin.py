import json
from re import S

from django.http import HttpResponse
from django.core.management import call_command

from .base import BaseState, EditModelMixin, ButtonsListMixin, SecretCodeMixin
from epsilonvi_bot import permissions as perm
from epsilonvi_bot import models as eps_models
from bot import models as bot_models
from bot.utils import send_group_message
from conversation import models as conv_models


def get_conversation_list_display(conversatoins_query):
    if conversatoins_query.count() == 0:
        return "سوالی وجود ندارد.\n"
    text = ""
    for c in conversatoins_query:
        l = f"{c.get_telegram_command()} - {c.subject}\n"
        text += l
    return text


def get_admin_list_display(admin_query):
    text = ""
    for idx, ad in enumerate(admin_query):
        l = f"{idx+1}- {ad.user.name} {ad.permissions}\n"
        text += l
    return text


class MessageMixin:
    def get_message_secret_code(self, state_obj, usage, back_state=None, chat_id=None):
        secret_code = eps_models.SecretCode.objects.create(
            admin=state_obj.user.admin, usage=usage
        )
        text = secret_code.display_command()
        inline_keyboard = state_obj._get_default_buttons(back_state)
        message = state_obj._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message

    def get_message_manager(self, state_obj, chat_id=None, states_list=[]):
        text = state_obj.text
        _list = []
        for s in states_list:
            btn = [(s.text, s.name, "")]
            _list.append(btn)
        inline_keyboard = state_obj._get_inline_keyboard_list(_list)
        inline_keyboard += state_obj._get_default_buttons()
        message = state_obj._get_message_dict(
            chat_id=chat_id,
            text=text,
            inline_keyboard=inline_keyboard,
        )
        # self.logger.error(f"{message=}")
        return message


class AdminBaseState(BaseState):
    ALL_PERMISSIONS = [
        perm.IsAdmin.name,
        perm.CanApproveConversation.name,
        perm.AddTeacher.name,
        perm.SendGroupMessage.name,
        perm.AddAdmin.name,
    ]

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.permissions = [
            perm.IsAdmin,
        ]

    def _has_permission(self):
        for _perm in self.permissions:
            permission = _perm()
            if not permission.has_permission(self.user):
                return False
        return True

    def _set_user_state(self, next_state):
        # if not isinstance(next_state, BaseState):
        #     return False
        _q = bot_models.State.objects.filter(name=next_state.name)
        if not _q.exists():
            call_command(self.INSERT_STATE_COMMAND)
            _q = bot_models.State.objects.filter(name=next_state.name)
            if not _q.exists():
                return False
        next_state_model = _q[0]
        self.user.userstate.state = next_state_model
        self.user.userstate.save()
        return True

    def message_unauthorized(self, chat_id=None):
        text = "اجازه دسترسی به این بخش را ندارید."
        message = self._get_message_dict(text=text, chat_id=chat_id)
        self.transition(message=message)
        return HttpResponse()

    def get_current_message_dict(self):
        message = self._get_message_dict(
            text=self.message.get("text", "None"),
            chat_id=self.chat_id,
        )
        return message

    def _get_default_buttons(self, back_button_state=None):
        _list = []
        _list.append([(AdminHome.text, AdminHome.name, "")])
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

    def _handle_unknown(self):
        return HttpResponse()

    def _handle_message(self):
        return HttpResponse()

    def handle(self):
        # self.logger.error(f"here")
        if not self._has_permission():
            msg = self._get_error_prefix()
            msg += f"unauthorized request: {self.user}"
            self.logger.error(msg=msg)
            return self.message_unauthorized(self.chat_id)
        # if not self.data_type in self.expected_input_types:
        #     return self.message_unexpected_input(self.chat_id)
        # # self.logger.error(f"XXX{self.data_type=}")
        # method = getattr(self, f"_handle_{self.data_type}", self._handle_unknown)
        # # self.logger.error(f"XXX{method=}")
        return super().handle()


class AdminHome(AdminBaseState):
    name = "ADMIN_home"
    text = "صفحه اصلی"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)
        self.expected_states = {
            AdminSendGroupMessage.name: AdminSendGroupMessage,
            AdminAdminManager.name: AdminAdminManager,
            AdminQuestionManager.name: AdminQuestionManager,
            AdminTeacherManager.name: AdminTeacherManager,
            AdminInfoManager.name: AdminInfoManager,
        }

    def _get_admin_actions_btns_list(self):
        _list = []
        # self.logger.error(self._get_error_prefix())
        for _, v in self.expected_states.items():
            action_class = v(self._tlg_res, self.user)
            if action_class._has_permission():
                btn = (action_class.text, action_class.name, "")
                # self.logger.error(f"{btn=}")
                _list.append([btn])
        return _list

    def get_message(self, chat_id=None):
        notifications = ""
        text = f"notification:\n{notifications}\n"
        _list = self._get_admin_actions_btns_list()
        inline_keyboard = self._get_inline_keyboard_list(_list)
        message = self._get_message_dict(
            chat_id=chat_id, text=text, inline_keyboard=inline_keyboard
        )
        return message


class AdminSendGroupMessage(AdminBaseState):
    name = "ADMIN_send_group_message"
    text = "ارسال پیام گروهی"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.permissions += [perm.SendGroupMessage]
        self.expected_input_types = [self.CALLBACK_QUERY, self.MESSAGE]
        self.expected_states = {
            AdminHome.name: AdminHome,
            AdminSendGroupMessageConfirm.name: AdminSendGroupMessageConfirm,
        }

    def get_message(self, chat_id=None):
        text = "پیام خود را ارسال کنید"
        inline_keyboard = self._get_default_buttons()
        message = self._get_message_dict(
            chat_id=chat_id, text=text, inline_keyboard=inline_keyboard
        )
        return message

    def _handle_message_text_type(self):
        next_state = AdminSendGroupMessageConfirm(self._tlg_res, self.user)
        current_message = self.get_current_message_dict()

        next_message = next_state.get_message(
            chat_id=self.chat_id,
            input_message=current_message,
        )
        self.transition(
            message=next_message, force_transition_type=self.TRANSITION_DEL_SEND
        )

        return HttpResponse("ok"), next_state

    def _handle_message_unkown_type(self):
        return HttpResponse("unknown_type"), self

    def _handle_message(self):
        # next_state = AdminSendGroupMessageConfirm(self._tlg_res, self.user)
        self.input_message_type = "text"
        handle_message_method = getattr(
            self,
            f"_handle_message_{self.input_message_type}_type",
            self._handle_message_unkown_type,
        )
        http_response, next_state = handle_message_method()
        check = self._set_user_state(next_state=next_state)
        if not check:
            msg = self._get_error_prefix()
            msg += f"{next_state=}\t{handle_message_method=}"
            self.logger.error(msg=msg)
        return http_response


class AdminSendGroupMessageConfirm(AdminBaseState):
    name = "ADMIN_send_group_message_confirm"
    text = "تایید و ارسال"

    SUCCESS_CODE = "sent"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

        self.permissions += [perm.SendGroupMessage]

        self.expected_input_types = [self.CALLBACK_QUERY]
        self.expected_states = {
            AdminHome.name: AdminHome,
            AdminSendGroupMessage.name: AdminSendGroupMessage,
        }

    def get_message(self, input_message: dict, chat_id=None):
        _list = [
            [(self.text, AdminHome.name, self.SUCCESS_CODE)],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons(AdminSendGroupMessage)
        message = self._get_message_dict(
            inline_keyboard=inline_keyboard, **input_message
        )
        return message

    def _handle_callback_query(self):
        if self.callback_query_data == self.SUCCESS_CODE:
            message = self.get_current_message_dict()
            send_group_message(message=message)
            self.logger.error(f"group_message: {message}")
        return super()._handle_callback_query(
            force_transition_type=self.TRANSITION_DEL_SEND
        )


class AdminAdminBaseState(AdminBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.permissions += [perm.AddAdmin]
        self.expected_input_types = [self.CALLBACK_QUERY]
        self.expected_states = {
            AdminHome.name: AdminHome,
            AdminAdminManager.name: AdminAdminManager,
            AdminAdminAdd.name: AdminAdminAdd,
            AdminAdminList.name: AdminAdminList,
            AdminAdminDetail.name: AdminAdminDetail,
        }


class AdminAdminManager(AdminAdminBaseState):
    name = "ADMIN_admin_manager"
    text = "مدیریت ادمین ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None):
        # self.logger.error(self._get_error_prefix())
        text = self.text
        _list = [
            [(AdminAdminAdd.text, AdminAdminAdd.name, "")],
            [(AdminAdminList.text, AdminAdminList.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons()
        message = self._get_message_dict(
            chat_id=chat_id,
            text=text,
            inline_keyboard=inline_keyboard,
        )
        # self.logger.error(f"{message=}")
        return message


class AdminAdminList(AdminAdminBaseState):
    name = "ADMIN_admin_list"
    text = "مشاهده تمام ادمین ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_admin_list_buttons(self, admin_query):
        _list = []
        for idx, ad in enumerate(admin_query):
            btn = (
                f"{idx+1}- {ad.user.name} ویرایش دسترسی",
                AdminAdminDetail.name,
                {"admin": ad.pk},
            )
            _list.append([btn])
        il_list = self._get_inline_keyboard_list(_list)
        return il_list

    def get_message(self, chat_id=None):
        _q = eps_models.Admin.objects.all().exclude(user=self.user)
        text = "لیست ادمین ها:\n"
        text += get_admin_list_display(_q)
        inline_keyboard = self.get_admin_list_buttons(_q)
        inline_keyboard += self._get_default_buttons(AdminAdminManager)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        _ad_id = self.callback_query_data.get("admin", None)
        if _ad_id and self.callback_query_next_state == AdminAdminDetail.name:
            _q = eps_models.Admin.objects.filter(pk=_ad_id)
            if _q.exists():
                admin = _q[0]
                get_message_kwargs.update({"admin": admin})
        else:
            get_message_kwargs = {}  # why!?
        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class AdminAdminAdd(AdminBaseState):
    name = "ADMIN_admin_add"
    text = "تولید کد ادمین"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.permissions += [perm.AddAdmin]

        self.expected_input_types = [self.CALLBACK_QUERY]

        self.expected_states = {
            AdminHome.name: AdminHome,
            AdminAdminManager.name: AdminAdminManager,
        }

    def get_message(self, chat_id=None):
        secret_code = eps_models.SecretCode.objects.create(
            admin=self.user.admin, usage="ADMIN"
        )
        text = secret_code.display_command()
        inline_keyboard = self._get_default_buttons(AdminAdminManager)
        message = self._get_message_dict(text=text, inline_keyboard=inline_keyboard)
        return message


class AdminAdminDetail(AdminAdminBaseState):
    name = "ADMIN_admin_detaii"
    text = "جزییات ادمین"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, admin, chat_id=None):
        text = f"ادمین: {admin.user.name}\nدسترسی ها: {admin.permissions}"
        admin_permissions = json.loads(admin.permissions)
        _list = []
        for p in self.ALL_PERMISSIONS:
            has_perm = True if (p in admin_permissions) else False
            char = "✅" if has_perm else ""
            add_or_remove = "rem" if has_perm else "add"
            btn = (
                f"{char} {p}",
                AdminAdminDetail.name,
                {"permission": p, "action": add_or_remove, "admin": admin.pk},
            )
            _list.append([btn])
        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons(AdminAdminList)
        message = self._get_message_dict(
            text=text, chat_id=chat_id, inline_keyboard=inline_keyboard
        )
        return message

    def add_or_remove_permisson(self, admin, permission, add_or_remove):
        if not (admin and permission):
            return False
        admin_permissions = json.loads(admin.permissions)
        if add_or_remove == "add":
            admin_permissions.append(permission)
        elif add_or_remove == "rem":
            admin_permissions.remove(permission)
        else:
            return False
        _json = json.dumps(admin_permissions)
        admin.permissions = _json
        admin.save()
        return True

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        if self.callback_query_next_state == AdminAdminDetail.name:
            action = self.callback_query_data.get("action", None)
            _ad_id = self.callback_query_data.get("admin", None)
            _perm_name = self.callback_query_data.get("permission", None)
            if action and _ad_id and _perm_name:
                _q = eps_models.Admin.objects.filter(pk=_ad_id)
                admin = _q[0] if _q.exists() else None

                permission = _perm_name if _perm_name in self.ALL_PERMISSIONS else None
                check = self.add_or_remove_permisson(
                    admin=admin, permission=permission, add_or_remove=action
                )
                if check:
                    get_message_kwargs = {"admin": admin}

        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class AdminQuestionManager(AdminBaseState):
    name = "ADMIN_question_manager"
    text = "مدیریت سوال ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

        self.expected_input_types.append(self.CALLBACK_QUERY)

        self.expected_states = {
            AdminQuestionList.name: AdminQuestionList,
            AdminHome.name: AdminHome,
        }

        self.permissions += [
            perm.CanApproveConversation,
        ]

    def get_message(self, chat_id=None):
        text = "عملیات مورد نظر را انتخاب کنید."
        _list = [
            [(AdminQuestionList.text, AdminQuestionList.name, "")],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons()
        message = self._get_message_dict(text=text, inline_keyboard=inline_keyboard)
        return message


class AdminQuestionList(AdminBaseState):
    name = "ADMIN_question_list"
    text = "لیست سوال ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)

        self.expected_states = {
            AdminQuestionManager.name: AdminQuestionManager,
            AdminQuestionList.name: AdminQuestionList,
            AdminQuestionDetail.name: AdminQuestionDetail,
            AdminHome.name: AdminHome,
        }

        self.permissions += [perm.CanApproveConversation]

    def get_message(
        self,
        chat_id=None,
        filters=[
            {"conversation_state__endswith": "-ADMIN"},
        ],
    ):
        _q = conv_models.Conversation.objects.all()
        for f in filters:
            _q = _q.filter(**f)

        text = "در انتظار بررسی\n"
        text += get_conversation_list_display(_q)
        _list = []
        inline_keyboard = self._get_default_buttons(AdminQuestionManager)
        message = self._get_message_dict(
            text=text, chat_id=chat_id, inline_keyboard=inline_keyboard
        )
        return message


class AdminQuestionDetail(AdminBaseState):
    name = "ADMIN_question_detail"
    text = "مشاهده سوال"

    APPROVE_BUTTON = "تایید"
    DENY_BUTTON = "رد"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)

        self.expected_states = {
            AdminQuestionManager.name: AdminQuestionList,
            AdminQuestionList.name: AdminQuestionList,
            AdminQuestionDetail.name: AdminQuestionDetail,
            AdminHome.name: AdminHome,
        }

        self.permissions += [perm.CanApproveConversation]

    def _get_conversation_messages(self, conversation):
        _conv = conversation
        _ques = _conv.question.all()[0]  # more than one message allowed
        _q = _conv.answer.all()
        _answ = _q[0] if _q.exists() else None
        _q = _conv.re_question.all()
        _ques_re = _q[0] if _q.exists() else None
        _q = _conv.re_answer.all()
        _answ_re = _q[0] if _q.exists() else None

        messages = []
        for m in [_ques, _answ, _ques_re, _answ_re]:
            if not m:
                break
            # self.logger.error(f"{m=}")
            # self.logger.error(f"{m.get_message_dict()=}")
            # self.logger.error(f"{m.message_type=}")
            message = self._get_message_dict(
                chat_id=self.chat_id, **m.get_message_dict()
            )
            _item = {"message_type": m.get_message_type_display(), "message": message}
            messages.append(_item)
        return messages

    def get_messages(self, conversation, chat_id=None) -> list:
        self.logger.error(f"{conversation=}")
        messages = self._get_conversation_messages(conversation=conversation)
        _list = []
        if conversation.conversation_state[-5:] == "ADMIN":
            btns = [
                (
                    self.APPROVE_BUTTON,
                    AdminQuestionDetail.name,
                    {"c_id": conversation.pk, "action": "appr"},
                ),
                (
                    self.DENY_BUTTON,
                    AdminQuestionDeny.name,
                    {"c_id": conversation.pk, "action": "deny"},
                ),
            ]
            _list.append(btns)
        text = "عملیات ها"
        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons(AdminQuestionManager)
        last_message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        messages.append({"message_type": "text", "message": last_message})
        return messages

    def _handle_send_messages(self, conversation):
        # self.logger.error(self._get_error_prefix())
        messages = self.get_messages(conversation=conversation)
        ids = []
        for m in messages:
            # self.logger.error(f"{m=}")
            message_type = m.get("message_type")
            # self.logger.error(f"{message_type=}")
            message = m.get("message")
            # self.logger.error(f"{message=}")
            method = getattr(self, f"send_{message_type}", self.send_unkown)
            _m_id = method(message)
            # self.logger.error(f"{_m_id=}")
            ids.append(_m_id)
        self.save_message_ids(delete_ids=ids)
        self._set_user_state(AdminQuestionDetail)

        return HttpResponse("ok")

    def _handle_callback_query(self, force_transition_type=None):
        if (
            self.callback_query_next_state == AdminQuestionDetail.name
            or self.callback_query_next_state == AdminQuestionDeny.name
        ):
            _cb_data = self.callback_query_data
            _action = _cb_data.get("action", None)
            _c_id = _cb_data.get("c_id", None)
            _q = conv_models.Conversation.objects.filter(pk=_c_id)
            conversation = _q[0] if _q.exists else None

            if not conversation:
                return self.message_error()
            if not _action or not _c_id:
                return self.message_error()

            _cs = conversation.conversation_state.split("-")[0]
            _help = {
                "Q": "question",
                "A": "answer",
                "RQ": "re_question",
                "RA": "re_answer",
            }

            if _action == "appr" and conversation.conversation_state[-5:] == "ADMIN":
                conversation.set_next_state()
                conversation.admins.add(self.user.admin)
                setattr(conversation, f"{_help[_cs]}_approved_by", self.user.admin)
                conversation.save()
                self._handle_delete_messages()
                next_state = AdminQuestionList(self._tlg_res, self.user)
                self._set_user_state(next_state=next_state)
                next_message = next_state.get_message()
                self.send_text(next_message)
                return HttpResponse("ok")

            elif _action == "deny" and conversation.conversation_state[-5:] == "ADMIN":
                # conversation.set_prev_state()
                conversation.admins.add(self.user.admin)
                conversation.working_admin = self.user.admin
                conversation.save()

            else:
                return self.message_error()

        else:
            return super()._handle_callback_query(force_transition_type)


class AdminQuestionDeny(AdminBaseState):
    name = "ADMIN_question_deny"
    text = "به صورت مختصر دلیل رد این پرسش یا پاسخ را توضیح دهید (فقط متن)."

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.MESSAGE)

        self.expected_states = {
            AdminQuestionManager.name: AdminQuestionList,
            AdminQuestionList.name: AdminQuestionList,
            AdminQuestionDetail.name: AdminQuestionDetail,
            AdminHome.name: AdminHome,
        }

        self.permissions += [perm.CanApproveConversation]

    def get_message(self, chat_id=None):
        text = self.text
        return self._get_message_dict(text=text)

    def _handle_message(self):
        _m = bot_models.Message.objects.create(
            text=self.input_text,
            message_id=self.message_id,
            chat_id=self.chat_id,
            from_id=self.user,
        )
        _q = conv_models.Conversation.objects.filter(working_admin=self.user.admin)
        if not _q.exists():
            return HttpResponse("nok")
        if _q.count() > 1:
            msg = self._get_error_prefix()
            msg += f"admin got more than one working converstation {self.user}"
            self.logger.error(msg=msg)
        conversation = _q[0]
        conversation.admin_response.add(_m)
        conversation.working_admin = None
        conversation.set_prev_state()
        conversation.save()
        self._handle_delete_messages()
        data = self._get_message_dict(message_id=self.message_id)
        self.delete_message(data)
        return HttpResponse("ok")


class AdminTeacherBaseState(AdminBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.permissions += [perm.AddTeacher]
        self.expected_input_types = [self.CALLBACK_QUERY]
        self.expected_states = {
            AdminHome.name: AdminHome,
            AdminTeacherManager.name: AdminTeacherManager,
            AdminTeacherAdd.name: AdminTeacherAdd,
            AdminTeacherList.name: AdminTeacherList,
            AdminTeacherDetail.name: AdminTeacherDetail,
        }


class AdminTeacherManager(MessageMixin, AdminTeacherBaseState):
    name = "ADMIN_teacher_manager"
    text = "مدیریت معلم ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None):
        state_list = [AdminTeacherAdd, AdminTeacherList]
        message = self.get_message_manager(
            state_obj=self, chat_id=chat_id, states_list=state_list
        )
        return message


class AdminTeacherAdd(SecretCodeMixin, AdminTeacherBaseState):
    name = "ADMIN_teacher_add"
    text = "تولید کد معلم"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None):
        message = self.get_secret_code(
            self,
            "TCHER",
            back_state=AdminTeacherManager,
            home_state=AdminHome,
            chat_id=chat_id,
        )
        return message


class AdminTeacherList(AdminTeacherBaseState):
    name = "ADMIN_teacher_list"
    text = "لیست معلمین"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None):
        # TODO add paging
        _q_active = eps_models.Teacher.objects.filter(is_active=True)
        _q_inavtive = eps_models.Teacher.objects.filter(is_active=False)
        _q = _q_active.union(_q_inavtive)

        text = "لیست معلمین:\n"
        _list = []
        if not _q.exists():
            pass
        for idx, t in enumerate(_q):
            is_active_char = "✔️" if t.is_active else "❌"
            is_active_text = "فعال" if t.is_active else "غیر فعال"
            btn = (
                f"{idx+1}- {is_active_char} {t.user.name}",
                AdminTeacherDetail.name,
                {"teacher": t.pk},
            )
            _list.append([btn])
            l = f"{idx+1}- {is_active_text} {t.user.name}\n"
            text += l
        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons(
            back_button_state=AdminTeacherManager
        )
        message = self._get_message_dict(
            text=text, chat_id=chat_id, inline_keyboard=inline_keyboard
        )
        return message

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        self.logger.error(f"{self.callback_query_data=}")
        teacher_pk = self.callback_query_data.get("teacher", None)
        if teacher_pk:
            _q = eps_models.Teacher.objects.filter(pk=teacher_pk)
            if _q.exists():
                teacher = _q[0]
                get_message_kwargs = {"teacher": teacher}
        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class AdminTeacherDetail(AdminTeacherBaseState):
    name = "ADMIN_teacher_detail"
    text = "جزيیات معلم"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, teacher, field=None, chat_id=None):
        text = f"نام: {teacher.user.name}\n"
        active_text = "فعال" if teacher.is_active else "غیر فعال"
        text += f"وضعیت: {active_text}\n"
        text += f"درس ها:\n"

        _list = []
        active_char = "✅" if teacher.is_active else ""
        inactive_char = "" if teacher.is_active else "✅"
        btn_active = (
            f"فعال {active_char}",
            AdminTeacherDetail.name,
            {"teacher": teacher.pk, "action": "activate"},
        )
        btn_inactive = (
            f"غیر فعال {inactive_char}",
            AdminTeacherDetail.name,
            {"teacher": teacher.pk, "action": "deactivate"},
        )
        _list.append([btn_active, btn_inactive])
        # field subjects list
        _q_tcher_subjects = teacher.subjects.all()

        mth_btn = [
            "درس های رشته ریاضی",
            AdminTeacherDetail.name,
            {"teacher": teacher.pk, "tab": "MTH", "action": "tab"},
        ]
        bio_btn = [
            "درس های رشته تجربی",
            AdminTeacherDetail.name,
            {"teacher": teacher.pk, "tab": "BIO", "action": "tab"},
        ]
        eco_btn = [
            "درس های رشته انسانی",
            AdminTeacherDetail.name,
            {"teacher": teacher.pk, "tab": "ECO", "action": "tab"},
        ]
        gen_btn = [
            "درس های عمومی",
            AdminTeacherDetail.name,
            {"teacher": teacher.pk, "tab": "GEN", "action": "tab"},
        ]
        _fields_list = ["MTH", "BIO", "ECO", "GEN"]
        _fields_btns = [mth_btn, bio_btn, eco_btn, gen_btn]
        for _f, _b in zip(_fields_list, _fields_btns):
            count = _q_tcher_subjects.filter(field=_f).count()
            _b[0] += f" ({count})"

        if field:
            for _field, _field_btn in zip(_fields_list, _fields_btns):
                if _field == field:
                    _q_all_subjects = eps_models.Subject.objects.filter(
                        field=field, is_active=True
                    )
                    _field_btn[2] = {"teacher": teacher.pk, "action": "fold"}
                    _list.append([_field_btn])
                    for s in _q_all_subjects:
                        is_active_char = "✅" if (s in _q_tcher_subjects) else ""
                        action_name = (
                            "rem_sub" if (s in _q_tcher_subjects) else "add_sub"
                        )
                        btn = (
                            f"- {is_active_char} {s} -",
                            AdminTeacherDetail.name,
                            {
                                "teacher": teacher.pk,
                                "tab": f"{field}",
                                "action": action_name,
                                "subject": s.pk,
                            },
                        )
                        _list.append([btn])
                else:
                    _list.append([_field_btn])
        else:
            _list.append([mth_btn])
            _list.append([bio_btn])
            _list.append([eco_btn])
            _list.append([gen_btn])

        _t = "["
        for s in _q_tcher_subjects:
            l = f"-{s}-"
            _t += l
        _t += "]"
        text += _t

        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons(AdminTeacherList)
        message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        return message

    def action_add_sub(self, message_kwargs, teacher):
        message_kwargs = self.action_tab(message_kwargs)
        subject_id = self.callback_query_data.get("subject", None)
        if not subject_id:
            return message_kwargs
        _q = eps_models.Subject.objects.filter(pk=subject_id)
        if not _q.exists():
            return message_kwargs
        subject = _q[0]

        if not teacher.subjects.filter(pk=subject.pk).exists():
            teacher.subjects.add(subject)
            teacher.save()

        return message_kwargs

    def action_rem_sub(self, message_kwargs, teacher):
        message_kwargs = self.action_tab(message_kwargs)
        subject_id = self.callback_query_data.get("subject", None)
        if not subject_id:
            return message_kwargs
        _q = eps_models.Subject.objects.filter(pk=subject_id)
        if not _q.exists():
            return message_kwargs
        subject = _q[0]

        if teacher.subjects.filter(pk=subject.pk).exists():
            teacher.subjects.remove(subject)
            teacher.save()
        return message_kwargs

    def action_tab(self, message_kwargs):
        tab = self.callback_query_data.get("tab", None)
        if tab and tab in eps_models.Subject.FIELDS:
            message_kwargs.update({"field": tab})
        return message_kwargs

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        action = self.callback_query_data.get("action")
        teacher = None
        if action:
            teacher_id = self.callback_query_data.get("teacher", None)
            if teacher_id:
                _q = eps_models.Teacher.objects.filter(pk=teacher_id)
                if _q.exists():
                    teacher = _q[0]
                    get_message_kwargs = {"teacher": teacher}
                    if action == "activate":
                        teacher.is_active = True
                        teacher.save()
                    elif action == "deactivate":
                        teacher.is_active = False
                        teacher.save()
                    elif action == "tab":
                        get_message_kwargs = self.action_tab(get_message_kwargs)
                    elif action == "add_sub":
                        get_message_kwargs = self.action_add_sub(
                            get_message_kwargs, teacher
                        )
                    elif action == "rem_sub":
                        get_message_kwargs = self.action_rem_sub(
                            get_message_kwargs, teacher
                        )
        if self.callback_query_next_state == AdminTeacherDetail.name:
            if not (action and teacher):
                self.callback_query_next_state = AdminTeacherList.name
        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class AdminInfoBaseState(AdminBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_states = {
            AdminHome.name: AdminHome,
            AdminInfoManager.name: AdminInfoManager,
            AdminInfoName.name: AdminInfoName,
            AdminInfoPhoneNumber.name: AdminInfoPhoneNumber,
            AdminInfoCreditCardNumber.name: AdminInfoCreditCardNumber,
        }


class AdminInfoManager(ButtonsListMixin, AdminInfoBaseState):
    name = "ADMIN_info_manager"
    text = "ویرایش مشخصات"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [
            self.CALLBACK_QUERY,
        ]

    def get_message(self, chat_id=None):
        text = f"نام: {self.user.name}\n"
        text += f"شماره تماس: {self.user.phone_number}\n"
        text += f"شماره کارت: {self.user.admin.credit_card_number}\n"
        states = [AdminInfoName, AdminInfoPhoneNumber, AdminInfoCreditCardNumber]
        message = self.get_state_buttons(
            state_obj=self,
            states_list=states,
            home_state=AdminHome,
            chat_id=chat_id,
            text=text,
        )
        return message

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        if not self.callback_query_next_state == AdminHome.name:
            self.save_message_ids(
                update_ids=[
                    self.message_id,
                ]
            )
        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class AdminInfoName(EditModelMixin, AdminInfoBaseState):
    name = "ADMIN_info_name"
    text = "ویرایش نام"
    text_2 = "نام"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [
            self.MESSAGE,
        ]

    def get_message(self, chat_id=None):
        message = self.get_output_message(
            state_obj=self,
            field_name=self.text_2,
            home_state=AdminHome,
            back_state=AdminInfoManager,
            chat_id=chat_id,
        )
        return message

    def _handle_message(self):
        http_response = self.get_text_and_save(
            state_obj=self,
            model=self.user,
            model_field="name",
            next_state_cls=AdminInfoManager,
            exclude="password",
        )
        return http_response


class AdminInfoPhoneNumber(EditModelMixin, AdminInfoBaseState):
    name = "ADMIN_info_phone_number"
    text = "ویرایش شماره تماس"
    text_2 = "شماره تماس"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [
            self.MESSAGE,
        ]

    def get_message(self, chat_id=None):
        message = self.get_output_message(
            state_obj=self,
            field_name=self.text_2,
            home_state=AdminHome,
            back_state=AdminInfoManager,
            chat_id=chat_id,
        )
        return message

    def _handle_message(self):
        http_response = self.get_text_and_save(
            state_obj=self,
            model=self.user,
            model_field="phone_number",
            next_state_cls=AdminInfoManager,
            exclude="password",
        )
        return http_response


class AdminInfoCreditCardNumber(EditModelMixin, AdminInfoBaseState):
    name = "ADMIN_info_credit_card_number"
    text = "ویرایش شماره کارت"
    text_2 = "شماره کارت"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [
            self.MESSAGE,
        ]

    def get_message(self, chat_id=None):
        message = self.get_output_message(
            state_obj=self,
            field_name=self.text_2,
            home_state=AdminHome,
            back_state=AdminInfoManager,
            chat_id=chat_id,
        )
        return message

    def _handle_message(self):
        http_response = self.get_text_and_save(
            state_obj=self,
            model=self.user.admin,
            model_field="credit_card_number",
            next_state_cls=AdminInfoManager,
        )
        return http_response
