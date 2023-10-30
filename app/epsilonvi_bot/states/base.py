import os
import logging
import json
import requests
from datetime import datetime

from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.management import call_command

from bot import models as bot_models
from epsilonvi_bot import models as eps_models
from conversation import models as conv_models
from user.models import User


def compact(data):
    compact, _ = bot_models.CompactDictionary.objects.get_or_create(word=str(data))
    return compact.pk


def decompact(pk):
    if type(pk) == int:
        pass
    elif type(pk) == str and pk.isnumeric():
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

    INSERT_STATE_COMMAND = "insert_states"

    TRANSITION_UPDATE = "_trans_update"
    TRANSITION_DEL_SEND = "_trans_delsend"

    BACK_BTN_TEXT = "بازگشت"

    def __init__(self, telegram_response_body, user) -> None:
        # self.name = "base_state"
        self.expected_input_types = []
        self.expected_states = {}

        self._tlg_res = telegram_response_body
        self.data = {}
        self.data_type = None
        self.input_message_type = None
        self.input_text = None
        self.user = user
        self.chat_id = None
        self.message_id = None
        self.logger = logging.getLogger(__name__)
        self.set_info()

        self.transition_method_name = self.TRANSITION_UPDATE

    def _get_error_prefix(self):
        return f"[CUSTOM ERROR] [STATE {self.name=}]:\t"

    def _set_data_type(self):
        if "callback_query" in self._tlg_res.keys():
            self.data_type = "callback_query"
        elif "message" in self._tlg_res.keys():
            self.data_type = "message"
        else:
            self.data_type = "un-defiened"

    def _set_data(self):
        self._set_data_type()
        self.data = self._tlg_res[self.data_type]
        if self.data_type == self.MESSAGE:
            self.message = self._tlg_res[self.data_type]
        else:
            self.message = self._tlg_res[self.data_type]["message"]

    def _set_callback_query_data(self):
        if self.data_type == self.CALLBACK_QUERY:
            callback_query_data = self.data["data"]
            _data = decompact(callback_query_data)
            _data = _data if _data else callback_query_data
            _dict = json.loads(_data)
            self.callback_query_next_state = _dict["state"]
            self.callback_query_data = _dict["data"]

    def _set_input_text(self):
        if self.data_type == self.CALLBACK_QUERY:
            text = self.data["data"]
            _d = decompact(text)
            _data = _d if _d else text
            self.input_text = json.loads(_data)
            # self.logger.error(f"{self._get_error_prefix()} {text=} {_d=} {_data=}")
            self.callback_query_next_state = self.input_text["state"]
            self.callback_query_data = self.input_text["data"]
        else:
            self.input_text = self.data.get("text", None)

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
        **kwargs,
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
        if kwargs:
            message_dict.update(kwargs)
        return message_dict

    def _get_inline_keyboard_list(self, keyboard_data):
        inline_list = []
        for row in keyboard_data:
            l = []
            for text, state, data in row:
                data = {} if data == "" else data
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
            "voice": "sendAudio",
            "photo": "sendPhoto",
        }
        method = TELEGRAM_METHODS[url_type]
        url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_BOT_TOKEN")}/{method}'
        return url

    def _check_response(self, response, data):
        if response.ok:
            return True
        _des = json.loads(response.text).get("description", None)
        if _des:
            _res = _des.find("message is not modified:")
            if _res != -1:
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

    def _get_default_buttons(self):
        pass

    def get_message(self, chat_id=None):
        pass

    def message_error(self, chat_id=None, value=None):
        text = f"مشکلی پیش آمده {value}"
        data = self._get_message_dict(text=text, chat_id=chat_id)
        self.send_text(data)
        return HttpResponse()

    def message_unexpected_state(self, chat_id=None):
        return HttpResponse()

    def message_unexpected_input(self, chat_id=None):
        return HttpResponse()

    def send_voice(self, data):
        url = self._get_url("voice")
        res = requests.post(url=url, json=data)
        if self._check_response(res, data):
            res = json.loads(res.text)
            message_id = res["result"]["message_id"]
            return message_id

        return 0

    def send_photo(self, data):
        url = self._get_url("photo")
        res = requests.post(url=url, json=data)
        if self._check_response(res, data):
            res = json.loads(res.text)
            message_id = res["result"]["message_id"]
            return message_id

        return 0

    def send_text(self, data):
        url = self._get_url("send")
        res = requests.post(url=url, json=data)
        if self._check_response(res, data):
            res = json.loads(res.text)
            message_id = res["result"]["message_id"]
            return message_id

        return 0

    def send_unkown(self, data):
        return 0

    def update_text(self, data):
        url = self._get_url("update")
        res = requests.post(url=url, json=data)
        if self._check_response(res, data):
            return True
        return False

    def update_photo(self):
        pass  # TODO later

    def delete_message(self, data):
        url = self._get_url("delete")
        res = requests.post(url=url, json=data)
        if self._check_response(res, data):
            return True
        return False

    def _trans_update(self, message, message_type="text", message_id=None):
        if message_id:
            message.update({"message_id": message_id})
        else:
            message.update({"message_id": self.message_id})
        update_method = getattr(self, f"update_{message_type}")
        return update_method(message)

    def _trans_delsend(self, message, message_type, message_id=None):
        _message_id = message_id if message_id else self.message_id
        data = self._get_message_dict(message_id=_message_id)
        self.delete_message(data)

        send_method = getattr(
            self,
            f"send_{message_type}",
            self.send_unkown,
        )
        self.sent_message_id = send_method(message)
        return self.sent_message_id != 0

    def _handle_message(self):
        pass

    def _get_state_model(self, state_name):
        _q = bot_models.State.objects.filter(name=state_name)
        if not _q.exists():
            call_command(self.INSERT_STATE_COMMAND)
            _q = bot_models.State.objects.filter(name=state_name)
            if not _q.exists():
                return None
        state_model = _q[0]
        return state_model

    def transition(
        self, message, message_id=None, force_transition_type=None, message_type="text"
    ):
        if force_transition_type:
            _trans_type = force_transition_type
        else:
            _trans_type = self.transition_method_name

        trans_method = getattr(self, _trans_type)
        res = trans_method(
            message,
            message_id=message_id,
            message_type=message_type,
        )
        return res

    def save_message_ids(self, update_ids=[], delete_ids=[]):
        _dict = {"update": update_ids, "delete": delete_ids}
        _json = json.dumps(_dict)
        self.user.userstate.message_ids = _json
        self.user.userstate.save()

    def get_message_ids(self, key=None):
        message_ids = self.user.userstate.message_ids
        _dict = json.loads(message_ids)
        if key:
            return _dict.get(key)
        return _dict

    def _handle_callback_query(self, force_transition_type=None, get_message_kwargs={}):
        # self.logger.error(f"{self._get_error_prefix()} {self.callback_query_next_state=}")
        if not self.callback_query_next_state:
            # self.logger.error(f"here-")
            return self.message_unexpected_state()
        _q = bot_models.State.objects.filter(name=self.callback_query_next_state)

        next_state_model = self._get_state_model(
            state_name=self.callback_query_next_state
        )
        if not next_state_model:
            self.logger.error(f"here--{_q=}")
            return self.message_unexpected_state(self.chat_id)
        # self.logger.error(f"here")
        _ns = self.expected_states.get(next_state_model.name, None)
        if _ns:
            next_state = _ns(self._tlg_res, self.user)
        else:
            msg = self._get_error_prefix()
            msg += f"{next_state_model.name=} not found in expected states!"
            self.logger.error(msg)
            return HttpResponse("nok")
        if get_message_kwargs == {}:
            next_message = next_state.get_message()
        else:
            next_message = next_state.get_message(**get_message_kwargs)
        # self.logger.error(f"{next_message=} {next_state.name=}")
        check = self.transition(
            next_message, self.message_id, force_transition_type=force_transition_type
        )
        if check:
            self._set_user_state(next_state=next_state)
            return HttpResponse()

        return self.message_error(self.chat_id)

    def handle(self):
        if not self.data_type in self.expected_input_types:
            text = "انجام این عملیات امکان پذیر نیست."
            data = self._get_message_dict(chat_id=self.chat_id, text=text)
            self.send_text(data)
            return HttpResponse("Something went wrong")
        method = getattr(self, f"_handle_{self.data_type}")
        http_response = method()
        return http_response


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


class ButtonsListMixin:
    def get_state_buttons(
        self,
        state_obj,
        states_list,
        chat_id=None,
        text=None,
        home_state=None,
        back_state=None,
    ):
        text = text if text else state_obj.text
        _list = []
        for s in states_list:
            btn = (s.text, s.name, "")
            _list.append([btn])
        if home_state:
            btn = (home_state.text, home_state.name, "")
            _list.append([btn])
        if back_state:
            btn = (state_obj.BACK_BTN_TEXT, back_state.name, "")
            _list.append([btn])
        inline_keyboard = state_obj._get_inline_keyboard_list(_list)
        message = state_obj._get_message_dict(
            text=text, chat_id=chat_id, inline_keyboard=inline_keyboard
        )
        return message

    def get_buttons_paging(self):
        pass


class EditModelMixin(ButtonsListMixin):
    def get_text_and_save(
        self, state_obj, model, model_field, next_state_cls, exclude=None
    ):
        # get input
        new_value = state_obj.input_text
        # validate input
        setattr(model, model_field, new_value)
        try:
            model.clean_fields(exclude=exclude)
        except ValidationError as err:
            state_obj.message_error(
                chat_id=state_obj.chat_id,
                value=f"validation error: {err.message_dict}",
            )
            http_response = HttpResponse("nok")
        else:
            model.save()
            http_response = HttpResponse("ok")

        # delete self message
        data = state_obj._get_message_dict(
            chat_id=state_obj.chat_id, message_id=state_obj.message_id
        )
        state_obj.delete_message(data)
        # transition to the last message
        update_message = state_obj.get_message_ids("update")[0]
        next_state = next_state_cls(state_obj._tlg_res, state_obj.user)
        next_message = next_state.get_message()
        state_obj.transition(next_message, message_id=update_message)
        state_obj._set_user_state(next_state_cls)
        return http_response

    def get_output_message(
        self, state_obj, field_name, home_state=None, back_state=None, chat_id=None
    ):
        text = f"{field_name} خود را وارد کنید."
        message = self.get_state_buttons(
            state_obj=state_obj,
            states_list=[],
            text=text,
            home_state=home_state,
            back_state=back_state,
            chat_id=chat_id,
        )
        return message


class SecretCodeMixin(ButtonsListMixin):
    def get_secret_code(
        self, state_obj, usage, back_state=None, home_state=None, chat_id=None
    ):
        secret_code = eps_models.SecretCode.objects.create(
            admin=state_obj.user.admin, usage=usage
        )
        text = secret_code.display_command()
        message = self.get_state_buttons(
            state_obj=state_obj,
            states_list=[],
            text=text,
            home_state=home_state,
            back_state=back_state,
            chat_id=chat_id,
        )
        return message


class MessageTypeMixin(object):
    def _get_message_type(self, message):
        if type(message) != dict:
            return False
        if "text" in message.keys():
            return "text"
        elif "voice" in message.keys():
            return "voice"
        elif "photo" in message.keys():
            return "photo"
        else:
            # not supported types
            return "other"

    def _handle_base_type(self, user, message_model, conversation_id=None):
        try:
            if conversation_id:
                conversation = conv_models.Conversation.objects.get(pk=conversation_id)
                conversation.question.all().delete()
            else:
                conversation = conv_models.Conversation.objects.get(
                    student=user.student, conversation_state="Q-STDNT-DRFT"
                )
        except ObjectDoesNotExist as err:
            return None
        else:
            conversation.question.all().delete()
            conversation.question.add(message_model)
            conversation.save()
            return conversation

    def _handle_text_type(
        self, message_id, chat_id, user, input_text, conversation_id=None
    ):
        _m = bot_models.Message.objects.create(
            message_id=message_id,
            chat_id=chat_id,
            from_id=user,
            text=input_text,
            message_type="TXT",
        )
        return self._handle_base_type(
            user, message_model=_m, conversation_id=conversation_id
        )

    def _handle_photo_type(self, data, message_id, chat_id, user, conversation_id=None):
        photo = data.get("photo", None)[-1]
        file = bot_models.File.objects.create(
            file_id=photo.get("file_id"),
            file_unique_id=photo.get("file_unique_id"),
            file_type="PHO",
        )
        _m_dict = {
            "message_id": message_id,
            "chat_id": chat_id,
            "from_id": user,
            "message_type": "PHO",
        }
        caption = data.get("caption", None)
        if caption:
            _m_dict.update({"caption": caption})

        _m = bot_models.Message.objects.create(**_m_dict)
        _m.files.add(file)
        _m.save()

        return self._handle_base_type(
            user, message_model=_m, conversation_id=conversation_id
        )

    def _handle_voice_type(self, data, message_id, chat_id, user, conversation_id=None):
        voice = data.get("voice", None)
        file = bot_models.File.objects.create(
            file_id=voice.get("file_id"),
            file_unique_id=voice.get("file_unique_id"),
            file_type="VOC",
            duration=voice.get("duration"),
        )
        _m_dict = {
            "message_id": message_id,
            "chat_id": chat_id,
            "from_id": user,
            "message_type": "VOC",
        }
        caption = data.get("caption", None)
        if caption:
            _m_dict.update({"caption": caption})

        _m = bot_models.Message.objects.create(**_m_dict)
        _m.files.add(file)
        _m.save()

        return self._handle_base_type(
            user, message_model=_m, conversation_id=conversation_id
        )

    def _handle_other_type(self):
        return None


class ConversationDetailMixin:
    def __get_conversation_messages_dict(self, conversation: conv_models.Conversation):
        _dict = {
            "question": conversation.question.all(),
            "answer": conversation.answer.all(),
            "re_question": conversation.re_question.all(),
            "re_answer": conversation.re_answer.all(),
            "denied_responses": conversation.denied_responses.all(),
        }
        return _dict

    def _get_conversation_messages(
        self, conversation: conv_models.Conversation, state_object, chat_id
    ):
        help_dict = {
            "question": "پرسش",
            "answer": "پاسخ",
            "re_question": "ادامه پرسش",
            "re_answer": "پاسخ تکمیلی",
            "denied_responses": "توضیحات ادمین",
        }

        _mess = self.__get_conversation_messages_dict(conversation)
        _output = []
        for k, messages in _mess.items():
            if k == "denied_responses":
                continue
            for m in messages:
                message = state_object._get_message_dict(
                    chat_id=chat_id, **m.get_message_dict()
                )
                _item = {
                    "message_type": m.get_message_type_display(),
                    "message": message,
                }
                _output.append(_item)
        return _output

    def get_messages(self, conversation: conv_models.Conversation, chat_id):
        return []
