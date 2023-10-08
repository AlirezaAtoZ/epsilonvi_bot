from datetime import datetime
from django.http import HttpResponse

# from . import states
from .states import States, Commands, StartCommand
from bot import models as bot_models
from user import models as user_models
from epsilonvi_bot import models as epsilonvi_bot_models


class BaseHandler:
    name: str
    is_done: bool

    def __init__(self, request_body) -> None:
        self.request_body = request_body
        self.update_id = request_body["update_id"]


class BaseFromHandler(BaseHandler):
    """
    base handler for the requests that contain a from object which leads to having a active user.
    """

    data_key: str
    user_state: bot_models.UserState

    def __init__(self, request_body) -> None:
        super().__init__(request_body)
        self.data = request_body[self.data_key]

    def _set_telegram_id_(self):
        self.user_telegram_id = self.data["from"]["id"]

    def _set_telegram_name_(self):
        self.user_telegram_name = self.data["from"]["first_name"]

    def _set_chat_id_(self):
        self.chat_id = self.data["chat"]["id"]

    def _set_user_state_(self):
        self.user_state = bot_models.UserState.objects.get(user=self.user)

    def _set_or_create_user_(self):
        self.user, new_user = user_models.User.objects.get_or_create(
            telegram_id=self.user_telegram_id
        )
        _, _ = epsilonvi_bot_models.Student.objects.get_or_create(
            user = self.user, 
        )
        if new_user:
            self.user.name = self.data["from"]["first_name"]
            self.user.save()
            state = bot_models.State.objects.get(name=States.UNIDF_welcome.name)
            self.user_state = bot_models.UserState.objects.create(
                user=self.user, state=state
            )

    def _is_done_(self) -> bool:
        # check if the request is new
        self.update, new = bot_models.UpdateID.objects.get_or_create(
            update_id=self.update_id
        )
        if not new:
            if self.update.is_done:
                self.is_done = True
                return True
        self.is_done = False
        return False

    def _set_done_(self):
        self.update.is_done = True
        self.update.save()

    def _set_user_info_(self):
        self._set_telegram_id_()
        self._set_telegram_name_()
        self._set_chat_id_()
        self._set_or_create_user_()
        self._set_user_state_()

    def _pre_run_(self):
        pass

    def _run_(self) -> HttpResponse:
        pass

    def _post_run_(self):
        pass

    def handle(self) -> HttpResponse:
        self._is_done_()
        if self.is_done:
            return HttpResponse("already processed the request.")
        self._set_user_info_()

        self._pre_run_()

        http_response = self._run_()

        self._post_run_()

        self._set_done_()

        return http_response


class MessageHandler(BaseFromHandler):
    name = "message"
    data_key = "message"

    def __init__(self, request_body) -> None:
        super().__init__(request_body)

    def _is_get_command_(self) -> tuple:
        if "entities" in self.data:
            entities = self.data["entities"]
            for entity in entities:
                if entity["type"] == "bot_command":
                    offset = entity["offset"]
                    length = entity["length"]
                    command = self.data["text"][
                        offset + 1 : offset + length
                    ]  # to by pass '/' character in commands
                    return True, command
        return False, None

    def _run_(self) -> HttpResponse:
        is_command, get_command = self._is_get_command_()
        if is_command:
            command_obj = getattr(Commands, get_command)
            self.name = "command"
            Command = command_obj(self)
            http_response = Command.handle()
        else:
            state_obj = getattr(States, self.user_state.state.name)
            state = state_obj(self)
            http_response = state.handle()
        return http_response


class CallbackQueryHandler(BaseFromHandler):
    name = "callback_query"
    data_key = "callback_query"

    def __init__(self, request_body) -> None:
        super().__init__(request_body)

    def _set_chat_id_(self):
        self.chat_id = self.data["message"]["chat"]["id"]

    def _run_(self) -> HttpResponse:
        state_obj = getattr(States, self.user_state.state.name)
        state = state_obj(self)
        http_response = state.handle()
        return http_response


class OtherHandler(BaseHandler):
    name = "other"

    def __init__(self, request_body) -> None:
        super().__init__(request_body)

    # TODO handle the exceptions

    def get_telegram_id(self):
        return None

    def get_telegram_name(self):
        return None


class Handlers:
    message = MessageHandler
    callback_query = CallbackQueryHandler
    other = OtherHandler


# TODO create a Handlers object in a more hardcode-less way!
def get_handlers():
    pass
