import logging
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from .states.base import BaseState
from .states.student import StudentHome
from .states.state_manager import StateManager
from user import models as usr_models
from epsilonvi_bot import models as eps_models
from bot import models as bot_models


class CommandBase(BaseState):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)
        self._tlg_res = telegram_response_body

    def handle(self):
        self.user.userstate.state = bot_models.State.objects.get(name="STDNT_home")
        self.user.userstate.save()
        state = StudentHome(self._tlg_res, self.user)
        message = state.get_message()
        # self.logger.error(f"{message=}")
        state.send_message(message)
        return HttpResponse()


class Home(CommandBase):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)


class Help(CommandBase):
    def __init__(self, telegram_response_body, user) -> None:
        super().__init__(telegram_response_body, user)


class CommandManager(StateManager):
    commands_mapping = {
        "home": Home,
        "start": Home,
        "help": Help,
    }

    def __init__(self, telegram_response_body) -> None:
        self._tlg_res = telegram_response_body
        self.command_handler = None
        self.logger = logging.getLogger(__name__)

    def _get_error_prefix(self):
        return "[CUSTOM ERROR] [COMMAND MANAGER]:\t"

    # def _get_or_create_user(self):
    #     if "callback_query" in self._tlg_res.keys():
    #         _from = self._tlg_res["callback_query"]["message"]["from"]
    #     else:
    #         _from = self._tlg_res["message"]["from"]

    #     self.telegram_id = _from["id"]
    #     try:
    #         user, is_new = usr_models.User.objects.get_or_create(
    #             telegram_id=self.telegram_id
    #         )
    #         if is_new:
    #             user.name = _from["first_name"]
    #             user.save()
    #             _ = eps_models.Student.objects.create(user=user)
    #             state = bot_models.State.objects.get(name="STDNT_home")
    #             _ = bot_models.UserState.objects.create(user=user, state=state)
    #     except ObjectDoesNotExist as err:
    #         msg = self._get_error_prefix()
    #         msg += f"DoesNotExist _get_or_create_user\t{_from=}"
    #         self.logger.error(msg=msg)
    #         user = is_new = None
    #     except Exception as err:
    #         msg = self._get_error_prefix()
    #         msg += f"_get_or_create_user\t{_from=} {err=}"
    #         self.logger.error(msg=msg)
    #         user = is_new = None
    #     return user, is_new

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

    def handle(self):
        command = self._get_command()
        if command and (command in self.commands_mapping.keys()):
            user, _ = self._get_or_create_user()
            self.command_handler = self.commands_mapping[command](self._tlg_res, user)
            # self.command_handler = self.commands_mapping[command](self._tlg_res)
            return self.command_handler.handle()

        msg = "[CUSTOM ERROR] [COMMAND MANAGER]\t"
        msg += f"command not found! {self._tlg_res}"
        self.logger.error(msg=msg)
        return HttpResponse()
