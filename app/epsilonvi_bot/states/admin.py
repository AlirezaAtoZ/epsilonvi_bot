import json
from django.http import HttpResponse
from django.core.management import call_command

from .base import (
    BaseState,
    ConversationDetailMixin,
    EditModelMixin,
    ButtonsListMixin,
    SecretCodeMixin,
    MessageTypeMixin,
)
from epsilonvi_bot import permissions as perm
from epsilonvi_bot import models as eps_models
from bot import models as bot_models
from bot import utils
from conversation import models as conv_models
from conversation.handlers import ConversationStateHandler
from billing.models import TeacherPayment


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
        l = f"{c.get_telegram_command()} - {c.subject} {_text}\n"
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
        perm.CanPayTeacher.name,
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


# admin home
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
            AdminTeacherPaymentManager.name: AdminTeacherPaymentManager,
            AdminInfoManager.name: AdminInfoManager,
        }

    def _get_admin_actions_btns_list(self):
        _list = []
        # self.logger.error(self._get_error_prefix())
        for _, v in self.expected_states.items():
            action_class = v(self._tlg_res, self.user)
            if action_class._has_permission():
                btn = (action_class.text, action_class.name, "")
                self.logger.error(f"{btn=}")
                # self.logger.error(f"{btn=}")
                _list.append([btn])
        return _list

    def get_message(self, chat_id=None):
        notifications = ""
        self.logger.error(f"here")
        text = f"notification:\n{notifications}\n"
        self.logger.error(f"here-")
        _list = self._get_admin_actions_btns_list()
        self.logger.error(f"here--")
        inline_keyboard = self._get_inline_keyboard_list(_list)
        self.logger.error(f"here---")
        message = self._get_message_dict(
            chat_id=chat_id, text=text, inline_keyboard=inline_keyboard
        )
        self.logger.error(f"here^")
        return message


# group message
class AdminSendGroupMessage(MessageTypeMixin, AdminBaseState):
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
        text = "پیام خود را ارسال کنید (تصویر یا متن)"
        inline_keyboard = self._get_default_buttons()
        message = self._get_message_dict(
            chat_id=chat_id, text=text, inline_keyboard=inline_keyboard
        )
        return message

    def _handle_base_type(self, user, message_model):
        special_message = eps_models.SpecialMessage.objects.create(
            message=message_model,
            admin=user.admin,
        )
        return special_message

    def _handle_text_type(self):
        return super()._handle_text_type(
            self.message_id, self.chat_id, self.user, self.input_text
        )

    def _handle_photo_type(self):
        return super()._handle_photo_type(
            self.data, self.message_id, self.chat_id, self.user
        )

    def _handle_message(self):
        self.input_message_type = self._get_message_type(self.data)
        handle_message_method = getattr(
            self,
            f"_handle_{self.input_message_type}_type",
            self._handle_other_type,
        )
        special_message = handle_message_method()
        if not special_message:
            return self.message_error()
        # delete usermessage
        data = self._get_message_dict(message_id=self.message_id)
        self.delete_message(data)
        # get next state message
        next_state = AdminSendGroupMessageConfirm(self._tlg_res, self.user)
        next_message = next_state.get_message(special_message)
        # find suitable send method and send next message
        send_method = getattr(self, f"send_{self.input_message_type}")
        send_method(next_message)
        # change user state
        check = self._set_user_state(next_state=next_state)
        if not check:
            msg = self._get_error_prefix()
            msg += f"{next_state=}\t{handle_message_method=}"
            self.logger.error(msg=msg)
        return HttpResponse("ok")


class AdminSendGroupMessageConfirm(MessageTypeMixin, AdminBaseState):
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

    def get_message(self, special_message, chat_id=None):
        _list = [
            [
                (
                    f"ارسال به دانش آموزان",
                    AdminHome.name,
                    {"target": "students", "sm": special_message.pk},
                )
            ],
            [
                (
                    f"ارسال به دبیران",
                    AdminHome.name,
                    {"target": "teachers", "sm": special_message.pk},
                )
            ],
            [
                (
                    f"ارسال به ادمین ها",
                    AdminHome.name,
                    {"target": "admins", "sm": special_message.pk},
                )
            ],
        ]
        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons(AdminSendGroupMessage)
        message = self._get_message_dict(
            inline_keyboard=inline_keyboard,
            **special_message.message.get_message_dict(),
            chat_id=chat_id,
        )
        return message

    def _handle_callback_query(self):
        target = self.callback_query_data.get("target", None)
        _sm = self.callback_query_data.get("sm", None)
        _q = eps_models.SpecialMessage.objects.filter(pk=_sm)
        if not _q.exists():
            return super()._handle_callback_query()
        else:
            special_message = _q[0]
        if target == "students":
            audience = eps_models.Student.objects.all()
        elif target == "teachers":
            audience = eps_models.Teacher.objects.filter(is_active=True)
        elif target == "admins":
            audience = eps_models.Admin.objects.filter(is_active=True)
        else:
            return super()._handle_callback_query()
        users = []
        for a in audience:
            users.append(a.user)
        utils.send_group_message(
            special_message.message.get_message_dict(),
            users,
            message_type=special_message.message.message_type,
        )

        return super()._handle_callback_query(
            force_transition_type=self.TRANSITION_DEL_SEND
        )


# admin manager
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
        _q = eps_models.Admin.objects.all()
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


# question manager
class AdminQuestionBaseState(AdminBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_states = {
            AdminHome.name: AdminHome,
            AdminQuestionManager.name: AdminQuestionManager,
            AdminQuestionList.name: AdminQuestionList,
            AdminQuestionDetail.name: AdminQuestionDetail,
            AdminQuestionDeny.name: AdminQuestionDeny,
        }


class AdminQuestionManager(AdminQuestionBaseState):
    name = "ADMIN_question_manager"
    text = "مدیریت سوال ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

        self.expected_input_types.append(self.CALLBACK_QUERY)

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


class AdminQuestionList(AdminQuestionBaseState):
    name = "ADMIN_question_list"
    text = "لیست سوال ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)

        self.permissions += [perm.CanApproveConversation]

    def get_message(
        self,
        chat_id=None,
    ):
        _q = conv_models.Conversation.objects.filter(
            conversation_state__endswith="COMP"
        ).exclude(conversation_state__contains="ADMIN")
        text = "در انتظار بررسی\n"
        text += get_conversation_list_display(_q)
        inline_keyboard = self._get_default_buttons(AdminQuestionManager)
        message = self._get_message_dict(
            text=text, chat_id=chat_id, inline_keyboard=inline_keyboard
        )
        return message


class AdminQuestionDetail(ConversationDetailMixin, AdminQuestionBaseState):
    name = "ADMIN_question_detail"
    text = "مشاهده سوال"

    APPROVE_BUTTON = "تایید"
    DENY_BUTTON = "رد"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.CALLBACK_QUERY)

        self.permissions += [perm.CanApproveConversation]

    def get_messages(
        self, conversation: conv_models.Conversation, chat_id=None
    ) -> list:
        # get conversation messages
        messages = self._get_conversation_messages(
            conversation=conversation, state_object=self, chat_id=chat_id
        )

        _list = []
        _ch = ConversationStateHandler(conversation)
        # the conversation is waiting for admin's response
        if _ch.is_waiting_on_admin():
            btns = [
                (
                    self.APPROVE_BUTTON,
                    AdminQuestionList.name,
                    {"c_id": conversation.pk, "action": "appr"},
                ),
                (
                    self.DENY_BUTTON,
                    AdminQuestionDeny.name,
                    {"c_id": conversation.pk, "action": "deny"},
                ),
            ]
            # add buttons to the last message btns
            _list.append(btns)
        # display conversation info in last message
        text = "اطلاعات این مکالمه:\n"
        text += f"دانش آموز: {conversation.student}\n"
        text += f"دبیر: {conversation.teacher}\n" if conversation.teacher else ""
        text += f"درس: {conversation.subject}\n"

        text += "عملیات ها:\n"
        inline_keyboard = self._get_inline_keyboard_list(_list)
        inline_keyboard += self._get_default_buttons(AdminQuestionManager)
        last_message = self._get_message_dict(
            text=text, inline_keyboard=inline_keyboard, chat_id=chat_id
        )
        messages.append({"message_type": "text", "message": last_message})
        return messages

    def _handle_send_messages(self, conversation):
        messages = self.get_messages(conversation=conversation)
        ids = []
        for m in messages:
            message_type = m.get("message_type")
            message = m.get("message")
            method = getattr(self, f"send_{message_type}", self.send_unkown)
            _m_id = method(message)
            ids.append(_m_id)
        self.save_message_ids(delete_ids=ids)
        self._set_user_state(AdminQuestionDetail)

        return HttpResponse("ok")

    def _handle_callback_query(self, force_transition_type=None):
        if (
            self.callback_query_next_state == AdminQuestionList.name
            or self.callback_query_next_state == AdminQuestionDeny.name
        ):
            _cb_data = self.callback_query_data
            _action = _cb_data.get("action", None)
            _c_id = _cb_data.get("c_id", None)
            conversation = conv_models.Conversation.objects.filter(pk=_c_id).first()

            if not conversation:
                return self.message_error()
            if not _action or not _c_id:
                return self.message_error()

            _conv_hand = ConversationStateHandler(conversation)

            if (
                _action == "appr"
                and _conv_hand.is_waiting_on_admin()
                and self.callback_query_next_state == AdminQuestionList.name
            ):
                # set the coversation state
                _conv_hand.handle(
                    "approve"
                )  # Q-STDNT-COMP -> Q-ADMIN-APPR | A-TCHER-COMP -> A-ADMIN-APPR | RQ-STDNT-COMP -> RQ-ADMIN_APPR | RA-TCHER-COMP ->RA-ADMIN-APPR
                # add admin to the list of admins which has been contributed to the conversation
                conversation.admins.add(self.user.admin)
                # TODO add approved by admin
                conversation.save()
                # delete last messages
                self._handle_delete_messages()
                # continiue

            elif _action == "deny" and _conv_hand.is_waiting_on_admin():
                _conv_hand.handle(
                    "deny"
                )  # Q-STDNT-COMP -> Q-ADMIN-DENY | A-TCHER-COMP -> A-ADMIN-DENY | RQ-STDNT-COMP -> RQ-ADMIN_DENY | RA-TCHER-COMP ->RA-ADMIN-DENY
                _conv_hand.handle()  # Q-ADMIN-DENY -> Q-ADMIN-DRFT | A-ADMIN-DENY -> A-ADMIN-DRFT | RQ-ADMIN_DENY -> RQ-ADMIN-DRFT | RA-ADMIN-DENY -> RA-ADMIN-DRFT
                # add admin to the list of admins which has been contributed to the conversation
                conversation.admins.add(self.user.admin)
                conversation.working_admin = self.user.admin
                conversation.save()
                return super()._handle_callback_query()

            else:
                return self.message_error()

        else:
            return super()._handle_callback_query(force_transition_type)


class AdminQuestionDeny(AdminQuestionBaseState):
    name = "ADMIN_question_deny"
    text = "به صورت مختصر دلیل رد این پرسش یا پاسخ را توضیح دهید (فقط متن)."

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types.append(self.MESSAGE)

        self.permissions += [perm.CanApproveConversation]

    def get_message(self, chat_id=None):
        text = self.text
        return self._get_message_dict(text=text, chat_id=chat_id)

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
        _conv_hand = ConversationStateHandler(conversation)
        _conv_hand.handle()  # Q-ADMIN-DRFT -> Q-ADMIN-COMP | A-ADMIN-DRFT -> A-ADMIN-COMP | RQ-ADMIN-DRFT -> RQ-ADMIN-COMP | RA-ADMIN-DRFT -> RA-ADMIN-COMP
        # add new reponse to the conversation responses
        conversation.denied_responses.add(_m)
        # remove convresation working admin
        conversation.working_admin = None

        conversation.save()

        self._handle_delete_messages()
        data = self._get_message_dict(message_id=self.message_id)
        self.delete_message(data)

        return HttpResponse("ok")


# teacher manager
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


# info manager
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


# teacher payments
class AdminTeacherPaymentBaseState(AdminBaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_input_types = [self.CALLBACK_QUERY]
        self.expected_states = {
            AdminHome.name: AdminHome,
            AdminTeacherPaymentManager.name: AdminTeacherPaymentManager,
            AdminTeacherPaymentDetail.name: AdminTeacherPaymentDetail,
            AdminTeacherPaymentHistory.name: AdminTeacherPaymentHistory,
        }
        self.permissions += [perm.CanPayTeacher]


class AdminTeacherPaymentManager(AdminTeacherPaymentBaseState):
    name = "ADMIN_teacher_payment_manager"
    text = "صورت حساب معلم ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None):
        text = "لیست معلم ها:\n"
        t_paymnts = conv_models.Conversation.get_teachers_payments_list()
        _list = []
        for idx, (tlg_id, amount) in enumerate(t_paymnts.items()):
            tcher = eps_models.Teacher.objects.filter(user__telegram_id=tlg_id).first()
            if not tcher:
                continue
            _line = f"{idx+1}\. {tcher.user.get_name_inline_link()} {int(amount)}\n"
            text += _line

            _btn = [
                f"{idx+1}. {tcher.user.name}",
                AdminTeacherPaymentDetail.name,
                {"user": tlg_id},
            ]
            _list.append([_btn])
        history_btn = [
            AdminTeacherPaymentHistory.text,
            AdminTeacherPaymentHistory.name,
            "",
        ]
        _list.append([history_btn])
        inline_btns = self._get_inline_keyboard_list(_list)
        inline_btns += self._get_default_buttons()
        message = self._get_message_dict(
            chat_id=chat_id,
            text=text,
            inline_keyboard=inline_btns,
            parse_mode="MarkdownV2",
        )
        return message

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        if self.callback_query_next_state == AdminTeacherPaymentDetail.name:
            uid = self.callback_query_data.get("user", None)
            if uid:
                teacher = eps_models.Teacher.objects.filter(
                    user__telegram_id=uid
                ).first()
                if teacher:
                    get_message_kwargs = {"teacher": teacher}
        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class AdminTeacherPaymentDetail(AdminTeacherPaymentBaseState):
    name = "ADMIN_teacher_payment_detail"
    text = "جرییات صورت حساب معلم"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, teacher, confirm=False, chat_id=None):
        text = f"نام: {teacher.user.get_name_inline_link()}\n"
        text += f"شماره کارت: {teacher.credit_card_number}\n"
        convs = teacher.get_unpaid_conversations()
        summary = ""
        convs_value = 0
        convs_ids = []
        for c in convs:
            convs_value += c.conversation_value()
            summary += c.get_telegram_command() + " "
            convs_ids.append(c.pk)
        text += f"مقدار: {int(convs_value)} تومان\n"
        text == f"مکالمات: {summary}\n"

        _list = []
        if confirm:
            btn = [
                "تایید",
                AdminTeacherPaymentDetail.name,
                {"tid": teacher.pk, "action": "pay", "cids": convs_ids},
            ]
        else:
            btn = [
                "پرداخت شد",
                AdminTeacherPaymentDetail.name,
                {"tid": teacher.pk, "action": "confirm"},
            ]
        _list.append([btn])
        inline_btns = self._get_inline_keyboard_list(_list)
        inline_btns += self._get_default_buttons(AdminTeacherPaymentManager)
        message = self._get_message_dict(
            text=text,
            inline_keyboard=inline_btns,
            chat_id=chat_id,
            parse_mode="MarkdownV2",
        )
        return message

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        # if it is paid -> create TeacherPayment entry
        action = self.callback_query_data.get("action", None)
        tid = self.callback_query_data.get("tid", None)
        cids = self.callback_query_data.get("cids", None)
        # self.logger.error(f"{tid=} {action=}")
        if self.callback_query_next_state == AdminTeacherPaymentDetail.name:
            if tid and action == "pay" and cids:
                teacher = eps_models.Teacher.objects.filter(pk=tid).first()
                conversations = conv_models.Conversation.objects.filter(
                    pk__in=cids, teacher=teacher
                )
                if teacher and conversations:
                    convs_value = 0
                    for c in conversations:
                        c.is_paid = True
                        c.save()
                        convs_value += c.conversation_value()
                    _ = TeacherPayment.objects.create(
                        teacher=teacher, amount=convs_value
                    )
                    get_message_kwargs = {"teacher": teacher}
            elif tid and action == "confirm":
                self.logger.error(f"here")
                teacher = eps_models.Teacher.objects.filter(pk=tid).first()
                if teacher:
                    self.logger.error(f"{teacher=}")
                    get_message_kwargs = {"teacher": teacher, "confirm": True}
            elif tid:
                teacher = eps_models.Teacher.objects.filter(pk=tid).first()
                if teacher:
                    get_message_kwargs = {"teacher": teacher}

        return super()._handle_callback_query(force_transition_type, get_message_kwargs)


class AdminTeacherPaymentHistory(AdminTeacherPaymentBaseState):
    name = "ADMIN_teacher_payment_history"
    text = "تمام پرداخت ها"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def get_message(self, chat_id=None):
        text = "لیست پرداخت ها\n"
        teacher_payments = TeacherPayment.objects.all()
        for idx, tp in enumerate(teacher_payments):
            _line = f"{idx+1}- دبیر: {tp.teacher.user.name} تاریخ پرداخت: {tp.date} مقدار پرداخت شده: {tp.amount}\n"
            text += _line
        inline_btns = self._get_default_buttons(AdminTeacherPaymentManager)
        message = self._get_message_dict(
            chat_id=chat_id, text=text, inline_keyboard=inline_btns
        )
        return message
