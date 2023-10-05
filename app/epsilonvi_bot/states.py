import os
import json
import requests
from datetime import datetime

from django.http import HttpResponse

# from .handlers import BaseHandler
from bot import models as bot_models


class BaseState:
    name: str
    CALLBACK_QUERY = "callback_query"
    KEYBOARD = "keyboard"
    COMMAND = "command"
    expected_inputs: list

    def __init__(self, handler) -> None:
        self.expected_inputs = [
            self.COMMAND,
        ]
        self.handler = handler

    def _get_next_state_(self) -> bot_models.State:
        pass

    def handle(self) -> HttpResponse:
        pass

    def _get_message_(self) -> dict:
        pass

    def _get_url_(self, method=None, send_message=False, edit_message=False):
        if send_message:
            method = "sendMessage"
        elif edit_message:
            method = "editMessageText"
        url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/{method}'
        return url

    def _check_response_(self, response, data) -> bool:
        if response.ok:
            return True
        # os.mkdir("telegram_bad_responses")
        with open(
            os.path.join("telegram_bad_responses", f"{datetime.now()}.json"), "w"
        ) as f:
            print(response.text, file=f)
            print(data, file=f)
        return False

    def wrong_input_message(self):
        text = f"only {self.expected_inputs} inputs!"
        url = self._get_url_(send_message=True)
        chat_id = self.handler.chat_id

        data = {"chat_id": chat_id, "text": text}
        res = requests.post(url, json=data)

        self._check_response_(res, data)

    def _check_input_type_(self) -> bool:
        if self.handler.name in self.expected_inputs:
            return True
        self.wrong_input_message()
        return False


class UNIDFWelcomeState(BaseState):
    name = "UNIDF_welcome"

    def __init__(self, handler) -> None:
        super().__init__(handler)
        self.expected_inputs.append(self.CALLBACK_QUERY)

    def _get_message_(self) -> dict:
        # count = int(self.input_data["data"])

        # count = 0
        text = f"Hi, {self.handler.user.name}\nWelcome to epsilon bot!"
        inline_keyboard = [
            [{"text": "Edit name", "callback_data": f"{UNIDFEditInfoState.name}"}],
            [{"text": "Next", "callback_data": "next"}],
        ]
        reply_markup = {"inline_keyboard": inline_keyboard}
        return {"text": text, "reply_markup": reply_markup}

    def _get_next_state_(self) -> bot_models.State:
        next_state_name = self.handler.data["data"]
        next_state = bot_models.State.objects.get(name=next_state_name)
        return next_state

    def _set_user_state_(self, state: bot_models.State, message_ids=None):
        self.handler.user_state.state = state
        if message_ids:
            self.handler.user_state.message_ids = message_ids
        self.handler.user_state.save()

    def handle(self):
        if not self._check_input_type_():
            return HttpResponse("Almost Ok")

        nexr_state_model = self._get_next_state_()
        next_state_obj = getattr(States, nexr_state_model.name)
        next_state = next_state_obj(self.handler)

        # delete the last message
        message_id = self.handler.data["message"]["message_id"]
        url = self._get_url_("deleteMessage")
        data = {"chat_id": self.handler.chat_id, "message_id": message_id}
        res = requests.post(url=url, json=data)
        self._check_response_(res, data)

        # send the next message
        url = self._get_url_(send_message=True)
        next_message = next_state._get_message_()
        data = {"chat_id": self.handler.chat_id, **next_message}
        res = requests.post(url, json=data)
        self._check_response_(res, data)

        # chenge user state
        self._set_user_state_(nexr_state_model)

        return HttpResponse("ok")


class UNIDFEditInfoState(BaseState):
    name = "UNIDF_edit_info"

    def __init__(self, handler) -> None:
        super().__init__(handler)
        self.expected_inputs.append(self.CALLBACK_QUERY)

    def _get_message_(self):
        text = f"Name:\n{self.handler.user.name}"
        inline_keyboard = [
            [{"text": "Edit name", "callback_data": f"{UNIDFEditInfoNameState.name}"}],
            # [{"text": "Back", "callback_data": f"{UNIDFWelcomeState.name}"}],
        ]
        reply_markup = {"inline_keyboard": inline_keyboard}
        message = {"text": text, "reply_markup": reply_markup}

        return message

    def _get_next_state_(self) -> bot_models.State:
        next_state_name = self.handler.data["data"]
        next_state = bot_models.State.objects.get(name=next_state_name)
        return next_state

    def _set_user_state_(self, state: bot_models.State, message_ids=None):
        self.handler.user_state.state = state
        if message_ids:
            self.handler.user_state.message_ids = message_ids
        self.handler.user_state.save()

    def handle(self) -> HttpResponse:
        if not self._check_input_type_():
            return HttpResponse("Almost")
        nexr_state_model = self._get_next_state_()
        next_state_obj = getattr(States, nexr_state_model.name)
        next_state = next_state_obj(self.handler)

        # send next message
        next_message = next_state._get_message_()
        url = self._get_url_(send_message=True)
        data = {"chat_id": self.handler.chat_id, **next_message}
        res = requests.post(url, json=data)
        if self._check_response_(res, data):
            res_dict = json.loads(res.text)
            sent_message_id = res_dict["result"]["message_id"]

            # save messages
            message_id = self.handler.data["message"]["message_id"]
            message_ids = [message_id, sent_message_id]
            the_str = ""
            for message in message_ids:
                the_str += str(message) + ","
            else:
                the_str = the_str[:-1]
            self._set_user_state_(nexr_state_model, the_str)

        return HttpResponse("ok")


class UNIDFEditInfoNameState(UNIDFWelcomeState):
    name = "UNIDF_edit_info_name"

    def __init__(self, handler) -> None:
        super().__init__(handler)
        self.expected_inputs.append(self.KEYBOARD)

    def _get_message_(self) -> dict:
        text = "Please enter your name:"
        message = {"text": text}
        return message

    def handle(self):
        if not self._check_input_type_:
            return HttpResponse("Almost")
        nexr_state_model = bot_models.State.objects.get(name="UNIDF_edit_info")
        next_state_obj = getattr(States, nexr_state_model.name)
        next_state = next_state_obj(self.handler)

        # save new name
        new_name = self.handler.data["text"]
        self.handler.user.name = new_name
        self.handler.user.save()

        # get message ids
        current_message_id = self.handler.data["message_id"]
        message_ids = self.handler.user_state.message_ids
        message_ids = [int(x) for x in message_ids.split(",")]
        to_be_updated_id = message_ids[0]
        to_be_deleted_ids = [message_ids[1], current_message_id]

        # update
        message = next_state._get_message_()
        url = self._get_url_(edit_message=True)
        data = {
            "chat_id": self.handler.chat_id,
            "message_id": to_be_updated_id,
            **message,
        }
        res = requests.post(url, json=data)
        self._check_response_(res, data)

        # delete
        url = self._get_url_("deleteMessage")
        for m_id in to_be_deleted_ids:
            data = {"chat_id": self.handler.chat_id, "message_id": m_id}
            res = requests.post(url, json=data)
            self._check_response_(res, data)

        # set next state
        self._set_user_state_(nexr_state_model)

        return HttpResponse("ok")


class StartCommand(UNIDFWelcomeState):
    name = "start"

    def __init__(self, handler) -> None:
        super().__init__(handler)

    def handle(self) -> HttpResponse:
        next_state_model = bot_models.State.objects.get(name="UNIDF_welcome")
        next_state_obj = getattr(States, next_state_model.name)
        next_state = next_state_obj(self.handler)

        # send message
        next_message = next_state._get_message_()
        url = self._get_url_(send_message=True)
        data = {"chat_id": self.handler.chat_id, **next_message}
        res = requests.post(url, json=data)
        self._check_response_(res, data)

        # set next state
        self._set_user_state_(next_state_model)

        return HttpResponse("ok")


class States:
    UNIDF_welcome = UNIDFWelcomeState
    UNIDF_edit_info_name = UNIDFEditInfoNameState
    UNIDF_edit_info = UNIDFEditInfoState


class Commands:
    start = StartCommand
