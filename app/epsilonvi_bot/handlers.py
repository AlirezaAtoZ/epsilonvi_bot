import logging

from django.http import HttpResponse
from .states.state_manager import StateManager
from .commands import CommandManager


class BaseHandler:
    def __init__(self, telegram_response_body) -> None:
        self._tlg_res = telegram_response_body
        self.logger = logging.getLogger(__name__)


class Command(BaseHandler):
    def __init__(self, telegram_response_body) -> None:
        super().__init__(telegram_response_body)
    
    def handle(self):
        command_manager = CommandManager(self._tlg_res)
        return command_manager.handle()


class Message(BaseHandler):
    def __init__(self, telegram_response_body) -> None:
        super().__init__(telegram_response_body)
    
    def handle(self):
        state_manager = StateManager(self._tlg_res)
        return state_manager.handle()


class CallbackQuery(BaseHandler):
    def __init__(self, telegram_response_body) -> None:
        super().__init__(telegram_response_body)
    
    def handle(self):
        state_manager = StateManager(self._tlg_res)
        return state_manager.handle()


class Other(BaseHandler):
    def __init__(self, telegram_response_body) -> None:
        super().__init__(telegram_response_body)
    
    def handle(self):
        msg = "[CUSTOM ERROR] [OTHER HANDLER]\t"
        msg += f"{self._tlg_res}"
        self.logger.error(msg=msg)
        return HttpResponse("nok")


class HandlerManager:
    handler_mapping = {
        "command": Command,
        "message": Message,
        "callback_query": CallbackQuery,
        "other": Other,
    }

    def __init__(self, telegram_response_body) -> None:
        self._tlg_res = telegram_response_body
        self.handler = None

    def _is_command(self):
        if "entities" in self._tlg_res["message"].keys():
            entities = self._tlg_res["message"]["entities"]
            for entity in entities:
                if entity["type"] == "bot_command":
                    return True
        return False

    def _get_response_type(self) -> str:
        _keys = self._tlg_res.keys()
        if "callback_query" in _keys:
            if self._tlg_res["callback_query"]["message"]["chat"]["type"] == "private":
                return "callback_query"

        elif "message" in _keys:
            if self._tlg_res["message"]["chat"]["type"] == "private":
                if self._is_command():
                    return "command"
                return "message"

        return "other"

    def handle(self):
        _type = self._get_response_type()
        self.handler = self.handler_mapping[_type](self._tlg_res)
        http_response = self.handler.handle()
        return http_response
