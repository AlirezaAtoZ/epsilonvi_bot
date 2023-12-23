import logging
import re
import json

from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from urllib3 import HTTPResponse

from .states.base import BaseState
from .states.student import StudentHome, StudentQuestionDetail, StudentPackageManager
from .states.admin import AdminHome, AdminQuestionDetail
from .states.teacher import TeacherHome, TeacherQuestionDetail
from .states.state_manager import StateManager
from user import models as usr_models
from epsilonvi_bot import models as eps_models
from epsilonvi_bot import permissions as perm
from conversation import models as conv_models
from bot import models as bot_models
from billing import models as bil_models
from billing import zarinpal as zar


class CommandBase(BaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self._tlg_res = telegram_response_body

    def handle(self, action_value=None):
        # self.logger.error(f"{self.input_text}")

        if self.user.userstate.role == "ADMIN":
            _state = AdminHome
        elif self.user.userstate.role == "TCHER":
            _state = TeacherHome
        else:
            _state = StudentHome

        self.user.userstate.state = bot_models.State.get_state(_state.name)
        self.user.userstate.save()
        state = _state(self._tlg_res, self.user)
        message = state.get_message()
        # self.logger.error(f"{message=}")
        state.send_text(message)
        return HttpResponse()


class Home(CommandBase):
    command = "start"

    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self.expected_actions = ["hello_world", "admin", "teacher"]

    def _is_get_deeplink(self, text):
        p = re.compile(r"/start action_([\w]+)_([\w]+)")
        m = p.search(text)
        if m:
            return True, m.group(1), m.group(2)
        return False, "", ""

    def error(self, value=None):
        text = f"مشکلی پیش آمده {value}"
        message = self._get_message_dict(text=text, chat_id=self.chat_id)
        self.send_text(data=message)
        return HttpResponse()

    def buy(self, value=None):
        # self.logger.error(f"{value=}")
        package = conv_models.Package.objects.filter(is_active=True, pk=value).first()
        # self.logger.error(f"{package=}")
        if package:
            student_package = conv_models.StudentPackage.objects.create(
                package=package,
                student=self.user.student,
            )
            student_package.is_pending = False
            student_package.save()
            # self.logger.error(f"{student_package=}")

        # TODO check for zarinpal

        return super().handle()

    def admin(self, code):
        # self.logger.error("HERE")
        _q = eps_models.SecretCode.objects.filter(code=code, usage="ADMIN")
        if not _q.exists():
            return self.error()
        _q.delete()
        _p = [
            perm.IsAdmin.name,
        ]
        permissions = json.dumps(_p)
        # self.logger.error(f"{permissions=}")
        admin, _ = eps_models.Admin.objects.get_or_create(
            user=self.user,
        )
        admin.permissions = permissions
        admin.is_active = True
        admin.save()
        self.user.userstate.role = "ADMIN"
        self.user.userstate.save()
        next_state = AdminHome(self._tlg_res, self.user)
        # self.logger.error(f"{next_state=}")

        check = self._set_user_state(next_state=next_state)
        # self.logger.error(f"{check=}")

        next_message = next_state.get_message()
        # self.logger.error(f"{next_message}")

        next_state.send_text(next_message)
        if check:
            return HttpResponse("ok")
        return HTTPResponse("nok")

    def teacher(self, code):
        # self.logger.error("HERE")
        _q = eps_models.SecretCode.objects.filter(code=code, usage="TCHER")
        if not _q.exists():
            return self.error("کد ورود پیدا نشد")
        _q.delete()
        _p = [
            perm.IsTeacher.name,
        ]
        permissions = json.dumps(_p)
        # self.logger.error(f"{permissions=}")
        teacher, _ = eps_models.Teacher.objects.get_or_create(
            user=self.user,
        )
        teacher.permissions = permissions
        teacher.is_active = True
        teacher.save()
        self.user.userstate.role = "TCHER"
        self.user.userstate.save()
        next_state = TeacherHome(self._tlg_res, self.user)
        # self.logger.error(f"{next_state=}")

        check = self._set_user_state(next_state=next_state)
        # self.logger.error(f"{check=}")

        next_message = next_state.get_message()
        # self.logger.error(f"{next_message}")

        next_state.send_text(next_message)
        if check:
            return HttpResponse("ok")
        return HTTPResponse("nok")

    def verify(self, code):
        if code == 0:
            # when invoice has not found
            pass
        else:
            invoice = bil_models.Invoice.objects.filter(
                student_package__student=self.user.student, pk=code
            ).first()
            if invoice:
                succ = invoice.status in [100, 101]
                if succ:
                    text = f"بسته: {invoice.student_package.package.name} با موفقیت خریداری و به لیست بسته های شما اضافه شد."
                else:
                    text = f"در خرید بسته: {invoice.student_package.package.name} مشکلی پیش آمد. {invoice.get_status_display()}"
                message = self._get_message_dict(text=text)
                self.send_text(message)

    def handle(self, action_value=None):
        # self.logger.error(f"{self.input_text=}")
        _is_deeplink, action, value = self._is_get_deeplink(self.input_text)
        if _is_deeplink:
            method = getattr(self, action, None)
            if method:
                http_response = method(value)
            else:
                http_response = self.error("invalid deep link")
            return http_response

        return super().handle()


class Help(CommandBase):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)

    def handle(self, action_value=None):
        _p = [
            perm.IsAdmin,
        ]
        permissoins = json.dumps(_p)
        admin = eps_models.Admin.objects.get(
            user=self.user,
        )
        admin.permissions = permissoins
        admin.save()
        _q = bot_models.State.objects.filter(name="ADMIN_home")
        if not _q.exists():
            return HttpResponse()
        state = _q[0]
        self.user.userstate.state = state
        self.user.userstate.save()

        admin_home = AdminHome(self._tlg_res, self.user)
        message = admin_home.get_message()
        admin_home.send_text(message)

        return HttpResponse()

class CheckPackage(CommandBase):
    name = "check_package"

    def handle(self, *args, **kwargs):
        invoices = bil_models.Invoice.objects.filter(student_package__student=self.user.student)
        for invoice in invoices:
            zi = zar.Zarinpal(invoice)
            zi.get_telegram_url()
        next_state = StudentPackageManager(self._tlg_res, self.user)
        check = self._set_user_state(next_state=next_state)
        next_message = next_state.get_message()
        next_state.send_text(next_message)
        if check:
            return HttpResponse("ok")
        return HTTPResponse("nok")


class Conversation(CommandBase):
    name = "conv"

    def _handle_admin_conversation_detail(self, conversation):
        _conv_dtl_state = AdminQuestionDetail(self._tlg_res, self.user)
        http_response = _conv_dtl_state._handle_send_messages(conversation=conversation)
        return http_response

    def _handle_student_conversation_detail(self, conversation):
        if conversation.student == self.user.student:
            _conv_dtl_state = StudentQuestionDetail(self._tlg_res, self.user)
            http_response = _conv_dtl_state._handle_send_messages(
                conversation=conversation
            )
            return http_response
        else:
            text = "شما اجازه دسترسی به این قسمت را ندارید.\n /start"
            self.send_text({"chat_id": self.chat_id, "text": text})
            return HttpResponse("nok")

    def _handle_teacher_conversation_detail(self, conversation):
        if conversation.teacher is None or conversation.teacher == self.user.teacher:
            _conv_dtl_state = TeacherQuestionDetail(self._tlg_res, self.user)
            http_response = _conv_dtl_state._handle_send_messages(
                conversation=conversation
            )
            return http_response
        else:
            text = "شما اجازه دسترسی به این قسمت را ندارید.\n /start"
            self.send_text({"chat_id": self.chat_id, "text": text})
            return HttpResponse("nok")

    def handle(self, conversation_id):
        _q = conv_models.Conversation.objects.filter(pk=conversation_id)
        if not _q.exists():
            return HttpResponse("nok")
        user_role = self.user.userstate.get_role_display()
        method = getattr(self, f"_handle_{user_role}_conversation_detail")
        conversation = _q[0]
        http_response = method(conversation)
        return http_response


class ChangeAdmin(CommandBase):
    name = "change_admin"

    def handle(self, action_value=None):
        self.user.userstate.role = "ADMIN"
        self.user.userstate.save()
        return HttpResponse("ok")


class ChangeTeacher(CommandBase):
    name = "change_teacher"

    def handle(self, action_value=None):
        self.user.userstate.role = "TCHER"
        self.user.userstate.save()
        return HttpResponse("ok")


class ChangeStudent(CommandBase):
    name = "change_student"

    def handle(self, action_value=None):
        self.user.userstate.role = "STDNT"
        self.user.userstate.save()
        return HttpResponse("ok")


class CommandManager(StateManager):
    commands_mapping = {
        "home": Home,
        "start": Home,
        "help": Help,
        ChangeAdmin.name: ChangeAdmin,
        ChangeTeacher.name: ChangeTeacher,
        ChangeStudent.name: ChangeStudent,
        Conversation.name: Conversation,
        CheckPackage.name: CheckPackage,
    }

    def __init__(self, telegram_response_body) -> None:
        self._tlg_res = telegram_response_body
        self.command_handler = None
        self.logger = logging.getLogger(__name__)

    def _get_error_prefix(self):
        return "[CUSTOM ERROR] [COMMAND MANAGER]:\t"

    def _get_command(self):
        entities = self._tlg_res["message"]["entities"]
        for entity in entities:
            if entity["type"] == "bot_command":
                offset = entity["offset"]
                length = entity["length"]
                command = self._tlg_res["message"]["text"][offset + 1 : offset + length]
                break
        else:
            command = None
        return command

    def get_command_class(self, command):
        command_class = self.commands_mapping.get(command, None)
        # self.logger.error(f"{command_class=}")
        action_value = None
        if command_class:
            return command_class, action_value
        p = re.compile(r"([\w]+)_([\d]+)")
        m = p.search(command)
        # self.logger.error(f"{m=}")
        if m:
            action_name = m.group(1)
            # self.logger.error(f"{action_name=}")
            action_value = m.group(2)
            # self.logger.error(f"{action_value=}")
            _cmd_cls = self.commands_mapping.get(action_name, None)
            return _cmd_cls, action_value
        msg = self._get_error_prefix()
        msg += f"command not found! {self._tlg_res}"
        self.logger.error(msg=msg)
        return None, None

    def handle(self):
        command = self._get_command()
        user, _ = self._get_or_create_user()
        _cmd, action_value = self.get_command_class(command)
        if _cmd:
            self.command_handler = _cmd(self._tlg_res, user)
        else:
            return HttpResponse("nok")
        # self.command_handler = self.commands_mapping[command](self._tlg_res)
        # if user.lock:
        #     return HttpResponse()
        # else:
        #     http_response = HttpResponse("nok")
        #     try:
        #         user.lock = True
        #         user.save()
        #         http_response = self.command_handler.handle(action_value)
        #     except Exception as err:
        #         self.logger.error(err)
        #     else:
        #         http_response = HttpResponse("ok")
        #     finally:
        #         user.lock = False
        #         user.save()
        #         return http_response
        # # http_response = HttpResponse("nok")
        http_response = self.command_handler.handle(action_value)
        return http_response
