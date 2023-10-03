import os
import requests
from datetime import datetime

from django.http import HttpResponse

from . import states
from .states import States
from bot import models as bot_models
from user import models as user_models


class BaseHandler:
    name: str
    is_done: bool

    def __init__(self, data) -> None:
        self.update_id = data['update_id']


class BaseFromHandler(BaseHandler):
    """
    base handler for the requests that contain a from object which leads to having a active user.
    """
    user_state: str

    def __init__(self, data) -> None:
        super().__init__(data)
        self.data = data[self.name]
        self.user_telegram_id = self.get_telegram_id()
        self.user_telegram_name = self.get_telegram_name()
        self.user_chat_id = self.get_chat_id()

    def _get_telegram_id_(self):
        telegram_id = self.data['from']['id']
        return str(telegram_id)

    def _get_telegram_name_(self):
        telegram_name = self.data['from']['first_name']
        return str(telegram_name)

    def _get_chat_id_(self):
        chat_id = self.data['chat']['id']
        return str(chat_id)

    def _get_user_state_(self):
        self.user_state = bot_models.UserState.objects.get(user=self.user)

    def _get_or_create_user_(self):
        self.user, new_user = user_models.User.objects.get_or_create(
            telegram_id=self.user_telegram_id
        )
        if new_user:
            state = bot_models.State.objects.get(
                name=states.UNIDFStartState.name)
            self.user_state = bot_models.UserState.objects.create(
                user=self.user, state=state)

    def _is_done_(self) -> bool:
        # check if the request is new
        self.update, new = bot_models.UpdateID.objects.get_or_create(
            update_id=self.update_id)
        if not new:
            if self.update.is_done:
                self.is_done = True
        self.is_done = False

    def _set_done_(self):
        self.update.is_done = True
        self.update.save()

    # def _pre_process_(self):
    #     self._is_done_()

    # def _post_process_(self):
    #     self._set_done_()

    def handle(self) -> HttpResponse:
        self._is_done_()
        if self.is_done:
            return HttpResponse('already processed the request.')
        self._get_or_create_user_()
        self._get_user_state_()

        state_obj = getattr(States, self.user_state.name)
        state = state_obj(self.name, self.data, self.user, self.user_chat_id, self.user_state)
        http_response = state.handle()

        self._set_done_()

        return http_response


class MessageHandler(BaseFromHandler):
    name = 'message'

    def __init__(self, data) -> None:
        super().__init__(data)

    # def handle(self):
    #     state = states.UNIDFStartState()
    #     view = state.get_view()
    #     data = {'chat_id': self.user_chat_id}
    #     data.update(view)

    #     url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/sendMessage'
    #     res = requests.post(url=url, json=data)

    #     with open(f'{datetime.now()}.json', 'w', encoding="utf-8") as f:
    #         print(data, file=f)
    #         print(res.text, file=f)


class CallbackQueryHandler(BaseFromHandler):
    name = 'callback_query'

    def __init__(self, data) -> None:
        super().__init__(data)


class OtherHandler(BaseHandler):
    def __init__(self, data) -> None:
        super().__init__(data)

    # TODO handle the exceptions

    def get_telegram_id(self):
        return None

    def get_telegram_name(self):
        return None


class Handlers:
    message = MessageHandler
    callback_query = CallbackQueryHandler
    other = OtherHandler
