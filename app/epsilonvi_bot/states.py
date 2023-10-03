from datetime import datetime
import os
from django.http import HttpResponse
import requests


class BaseState:
    name: str
    expected_inputs: list
    CALLBACK_QUERY = 'callback_query'
    KEYBOARD = 'keyboard'
    COMMAND = 'command'

    def __init__(self, input_type, input_data, user, user_chat_id, user_state) -> None:
        self.input_type = input_type
        self.input_data = input_data
        self.user = user
        self.user_chat_id = user_chat_id
        self.user_state = user_state

    def _next_state_(self):
        pass

    def handle(self) -> HttpResponse:
        pass

    def _get_view_(self):
        pass

    def _get_url_(self, method):
        url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/{method}'
        return url


class UNIDFStartState(BaseState):
    name = "UNIDF_start"

    def __init__(self, input_type, input_data, user, user_chat_id, user_state) -> None:
        super().__init__(input_type, input_data, user, user_chat_id, user_state)

    def _get_view_(self):
        text = f"welcome\ncount: {self.input_data}"
        inline_keyboard = [
            [{'text': "increase ⏫",
                "callback_data": f"{int(self.input_data['data']) + 1}"}],
            [{'text': "reset 🔁", "callback_data": '0'}]]
        reply_markup = {'inline_keyboard': inline_keyboard}
        return {'text': text, 'reply_markup': reply_markup}

    def handle(self):
        view = self._get_view_()
        url = self._get_url_('sendMessage')

        data = {'chat_id': self.user_chat_id}
        data.update(view)

        res = requests.post(url, json=data)
        if not res.ok:
            with open(f'{datetime.now()}.json', 'w', encoding="utf-8") as f:
                print(data, file=f)
                print(res.text, file=f)

        return HttpResponse('ok')


class States:
    UNIDF_start = UNIDFStartState
