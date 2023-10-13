import os
import logging
import json
import requests
import zlib
from datetime import datetime

from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command

from bot import models as bot_models


def compact(data):
    compact, _ = bot_models.CompactDictionary.objects.get_or_create(word=str(data))
    return compact.pk

def decompact(pk):
    if type(pk) == "int":
        pass
    elif type(pk) == "str" and pk.isnumeric():
        pk = int(pk)
    else:
        return None
    try:
        data = bot_models.CompactDictionary.objects.get(pk=pk).word
    except ObjectDoesNotExist as err:
        data = None
    return data
    

class BaseState:
    name = ""
    text = ""
    MESSAGE = "message"
    CALLBACK_QUERY = "callback_query"
    COMMAND = "command"

    BACK_BTN_TEXT = "بازگشت"

    def __init__(self, telegram_response_body, user) -> None:
        # self.name = "base_state"
        self.expected_input_types = []
        self.expected_states = {}

        self._tlg_res = telegram_response_body
        self.data = {}
        self.input_type = None
        self.input_text = None
        self.user = user
        self.chat_id = None
        self.message_id = None
        self.logger = logging.getLogger(__name__)
        self.set_info()

    def _get_error_prefix(self):
        return f"[CUSTOM ERROR] [STATE {self.name=}]:\t"

    def _set_input_type(self):
        if "callback_query" in self._tlg_res.keys():
            self.input_type = "callback_query"
        elif "message" in self._tlg_res.keys():
            self.input_type = "message"
        else:
            self.input_type = "un-defiened"

    def _set_data(self):
        self._set_input_type()
        self.data = self._tlg_res[self.input_type]
        if self.input_type == self.MESSAGE:
            self.message = self._tlg_res[self.input_type]
        else:
            self.message = self._tlg_res[self.input_type]["message"]

    def _set_callback_query_data(self):
        if self.input_type == self.CALLBACK_QUERY:
            callback_query_data = self.data["data"]
            _data = decompact(callback_query_data)
            _data = _data if _data else callback_query_data
            _dict = json.loads(_data)
            self.callback_query_next_state = _dict["state"]
            self.callback_query_data = _dict["data"]

    def _set_input_text(self):
        if self.input_type == self.CALLBACK_QUERY:
            text = self.data["data"]
            _data = decompact(text)
            _data = _data if _data else text
            self.input_text = json.loads(text)
            self.callback_query_next_state = self.input_text["state"]
            self.callback_query_data = self.input_text["data"]
        else:
            self.input_text = self.data["text"]

    def set_info(self):
        self._set_data()
        self.chat_id = self.message["chat"]["id"]
        self.message_id = self.message["message_id"]
        self._set_input_text()

    def _get_message_dict(
        self,
        chat_id=None,
        message_id=None,
        text=None,
        reply_markup=None,
        inline_keyboard=None,
    ):
        message_dict = {}
        if chat_id:
            message_dict.update({"chat_id": chat_id})
        else:
            message_dict.update({"chat_id": self.chat_id})
        if message_id:
            message_dict.update({"message_id": message_id})
        if text:
            message_dict.update({"text": text})
        if reply_markup:
            message_dict.update({"reply_markup": reply_markup})
        if inline_keyboard:
            message_dict.update({"reply_markup": {"inline_keyboard": inline_keyboard}})
        return message_dict

    def _get_inline_keyboard_list(self, keyboard_data):
        inline_list = []
        for row in keyboard_data:
            l = []
            for text, state, data in row:
                d = {"state": state, "data": data}
                _data = json.dumps(d)
                if len(_data) > 63:
                    _data = compact(_data)
                    self.logger.debug(f"compact data: {_data}")

                btn = {"text": text, "callback_data": _data}
                l.append(btn)
            inline_list.append(l)
        return inline_list

    def _get_url(self, url_type):
        TELEGRAM_METHODS = {
            "send": "sendMessage",
            "update": "editMessageText",
            "delete": "deleteMessage",
        }
        method = TELEGRAM_METHODS[url_type]
        url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/{method}'
        return url

    def _check_response(self, response, data):
        if response.ok:
            return True
        folder = "telegram_bad_responses"
        try:
            os.mkdir(folder)
        except FileExistsError as err:
            pass
        file_path = os.path.join(folder, f"{datetime.now()}.log")
        with open(file_path, "w", encoding="UTF-8") as f:
            print(f"{response.text=} {data=}", file=f)
        msg = self._get_error_prefix()
        msg += f"check_response\n{response.text=} {data=}"
        self.logger.error(msg=msg)
        return False

    def get_message(self, chat_id=None):
        pass

    def send_message(self, data):
        url = self._get_url("send")
        res = requests.post(url=url, json=data)
        if self._check_response(res, data):
            res = json.loads(res.text)
            message_id = res["result"]["message_id"]
            return message_id

        return 0

    def update_message(self, data):
        url = self._get_url("update")
        res = requests.post(url=url, json=data)
        if self._check_response(res, data):
            return True
        return False

    def delete_message(self, data):
        url = self._get_url("delete")
        res = requests.post(url=url, json=data)
        if self._check_response(res, data):
            return True
        return False

    def _handle_message(self):
        pass

    def _handle_callback_query(self):
        if self.callback_query_next_state in self.expected_states.keys():
            next_state = self.expected_states[self.callback_query_next_state](
                self._tlg_res, self.user
            )
            data = self._get_message_dict(message_id=self.message_id)
            self.delete_message(data)

            next_message = next_state.get_message()
            self.sent_message_id = self.send_message(next_message)

            # TODO unkown state handler
            updated = False
            for _ in range(2):
                try:
                    self.user.userstate.state = bot_models.State.objects.get(
                        name=self.callback_query_next_state
                    )
                except ObjectDoesNotExist as err:
                    if updated:
                        msg = self._get_error_prefix()
                        msg += f"{self.callback_query_next_state=}\n"
                        msg += f"{err=}"
                        self.logger.error(msg)
                        break
                    call_command("insert_states")
                    updated = True
                else:
                    break
            self.user.userstate.save()
            return HttpResponse("ok")
        else:
            return HttpResponse()

    def handle(self):
        if not self.input_type in self.expected_input_types:
            text = "انجام این عملیات امکان پذیر نیست."
            data = self._get_message_dict(chat_id=self.chat_id, text=text)
            self.send_message(data)
            return HttpResponse("Something went wrong")
        method = getattr(self, f"_handle_{self.input_type}")
        http_response = method()
        return http_response
