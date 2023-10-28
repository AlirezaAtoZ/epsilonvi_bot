# import os
# import json
# import requests
# import logging
# from typing import Tuple
# from datetime import datetime

# from django.http import HttpResponse
# from django.db.models import Model

# from bot import models as bot_models
# from epsilonvi_bot import models as eps_models


# class BaseState:
#     name: str
#     input_type: str
#     expected_inputs: list
#     expected_next_states: list

#     CALLBACK_QUERY = "callback_query"
#     MESSAGE = "message"
#     COMMAND = "command"

#     def __init__(self, handler) -> None:
#         self.handler = handler
#         self.expected_inputs = [
#             self.COMMAND,
#         ]
#         self.input_type = handler.name
#         self.logger = logging.getLogger(__name__)
#         self.sent_message_id = None

#     def _get_url_(self, type="send") -> str:
#         TELEGRAM_METHODS = {
#             "send": "sendMessage",
#             "update": "editMessageText",
#             "delete": "deleteMessage",
#         }
#         method = TELEGRAM_METHODS[type]
#         url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/{method}'
#         return url

#     def _get_message_(self) -> str:
#         return ""

#     def _check_response_(self, response, data, type: str) -> bool:
#         if response.ok:
#             return True
#         # os.mkdir("telegram_bad_responses")
#         with open(
#             os.path.join("telegram_bad_responses", f"{datetime.now()}-{type}.json"), "w"
#         ) as f:
#             print(response.text, file=f)
#             print(data, file=f)
#         return False

#     def _create_callback_data_json_(self, state, data=""):
#         callback_data = {"state": state, "data": data}
#         callback_data = json.dumps(callback_data)
#         return callback_data

#     def _get_next_state_name_and_data_from_data_(self, data) -> Tuple[str, str]:
#         callback_data = json.loads(data)
#         next_state_name = callback_data["state"]
#         callback_data = callback_data["data"]
#         return next_state_name, callback_data

#     def _set_next_state_and_state_model_callback_query_(self) -> bool:
#         (
#             next_state_name,
#             self.callback_data,
#         ) = self._get_next_state_name_and_data_from_data_(self.handler.data["data"])
#         if next_state_name in self.expected_next_states:
#             try:
#                 self.next_state_model = bot_models.State.objects.get(
#                     name=next_state_name
#                 )
#             except ObjectDoesNotExist as e:
#                 msg = f"CUSTOM: State object does not exist!\n"
#                 msg += f"{self.handler.data=}\n"
#                 msg += f"{next_state_name=}\n"
#                 self.logger.error(msg=msg)
#             next_state_obj = getattr(States, next_state_name)
#             self.next_state = next_state_obj(self.handler)
#             return True
#         else:
#             self._wrong_input_message_(
#                 err_text=f"only {self.expected_next_states} inputs!"
#             )
#             msg = f"CUSTOM: A none expected input from callback query has entered!\n"
#             msg = f"{self.handler.user_state=}\n"
#             msg = f"{next_state_name=}\n"
#             self.logger.warning(msg=msg)
#             return False

#     def _set_next_state_and_state_model_message_(self) -> bool:
#         return True

#     def _set_next_state_and_state_model_(self) -> bool:
#         method = getattr(self, f"_set_next_state_and_state_model_{self.input_type}_")
#         result = method()
#         return result

#     def _set_user_state_(self, state_model, user=None):
#         if user is None:
#             user = self.handler.user
#         user_state = bot_models.UserState.objects.get(user=user)
#         user_state.state = state_model
#         user_state.save()

#     def _create_data_(
#         self, chat_id=None, message_id=None, text=None, inline_keyboard=[]
#     ) -> dict:
#         data = {}
#         if chat_id is None:
#             data.update({"chat_id": self.handler.chat_id})
#         else:
#             data.update({"chat_id": chat_id})
#         if message_id:
#             data.update({"message_id": message_id})
#         if text:
#             data.update({"text": text})
#         if inline_keyboard != []:
#             reply_markup = {"inline_keyboard": inline_keyboard}
#             data.update({"reply_markup": reply_markup})

#         return data

#     def _message_(self, type: str, data: dict):
#         url = self._get_url_(type)
#         response = requests.post(url, json=data)
#         if type == "send" and self._check_response_(response, data, type):
#             # self.logger.error(msg=f"CUSTUM:{response.text}")
#             response_dict = json.loads(response.text)
#             self.sent_message_id = int(response_dict["result"]["message_id"])

#     def _wrong_input_message_(self, err_text=None):
#         if err_text is None:
#             err_text = f"only {self.expected_inputs} inputs!"
#         data = self._create_data_(text=err_text)

#         self._message_("send", data)

#     def _check_input_type_(self) -> bool:
#         if self.input_type in self.expected_inputs:
#             return True
#         self._wrong_input_message_()
#         return False

#     def _run_callback_query_(self) -> HttpResponse:
#         return HttpResponse("undefined")

#     def _run_message_(self) -> HttpResponse:
#         return HttpResponse("undefined")

#     def handle(self) -> HttpResponse:
#         if not self._check_input_type_():
#             return HttpResponse("Wrong input type!")
#         check = self._set_next_state_and_state_model_()
#         if check:
#             if self.input_type == "message":
#                 http_response = self._run_message_()
#             elif self.input_type == "callback_query":
#                 http_response = self._run_callback_query_()
#             # method = getattr(self, f"_run_{self.input_type}_")
#             # http_response = method()
#             self._set_user_state_(self.next_state_model)
#             return http_response
#         return HttpResponse("Something went wrong with the states")


# class UNIDFWelcome(BaseState):
#     name = "UNIDF_welcome"

#     def __init__(self, handler) -> None:
#         super().__init__(handler)
#         self.expected_inputs.append(self.CALLBACK_QUERY)
#         self.expected_next_states = [States.UNIDF_edit_info.name, "UNIDF_next"]

#     def _get_message_(self) -> dict:
#         text = f"Hi, {self.handler.user.name}\nWelcome to epsilon bot!"
#         inline_keyboard = [
#             [
#                 {
#                     "text": "Edit Info",
#                     "callback_data": f"{self._create_callback_data_json_(States.UNIDF_edit_info.name)}",
#                 }
#             ],
#             [{"text": "Next", "callback_data": "next"}],
#         ]

#         reply_markup = {"inline_keyboard": inline_keyboard}

#         message = {"text": text, "reply_markup": reply_markup}

#         return message

#     def _run_callback_query_(self) -> HttpResponse:
#         next_message = self.next_state._get_message_()
#         data = {"chat_id": self.handler.chat_id}
#         data.update(next_message)
#         self._message_("send", data)
#         data = {
#             "chat_id": self.handler.chat_id,
#             "message_id": self.handler.data["message"]["message_id"],
#         }
#         self._message_("delete", data)

#         return HttpResponse("ok")


# class UNIDFEditInfo(BaseState):
#     name = "UNIDF_edit_info"

#     def __init__(self, handler) -> None:
#         super().__init__(handler)
#         self.expected_inputs.append(self.CALLBACK_QUERY)
#         self.expected_next_states = [
#             States.UNIDF_welcome.name,
#             States.UNIDF_edit_info_name.name,
#             States.UNIDF_edit_info_grade.name,
#             States.UNIDF_edit_info_phone_number.name,
#         ]

#     def _get_message_(self) -> dict:
#         inline_keyboard = [
#             [
#                 {
#                     "text": "Edit Name",
#                     "callback_data": self._create_callback_data_json_(
#                         States.UNIDF_edit_info_name.name
#                     ),
#                 }
#             ],
#             [
#                 {
#                     "text": "Edit Phone",
#                     "callback_data": self._create_callback_data_json_(
#                         States.UNIDF_edit_info_phone_number.name
#                     ),
#                 }
#             ],
#             [
#                 {
#                     "text": "Edit Grade",
#                     "callback_data": self._create_callback_data_json_(
#                         States.UNIDF_edit_info_grade.name
#                     ),
#                 }
#             ],
#             [
#                 {
#                     "text": "Back",
#                     "callback_data": self._create_callback_data_json_(
#                         States.UNIDF_welcome.name
#                     ),
#                 }
#             ],
#         ]

#         text = f"Name:\n{self.handler.user.name}\n"
#         text += f"Phone Number:\n{self.handler.user.phone_number}\n"
#         text += f"Grade:\n{self.handler.user.student.grade}\n"

#         message = {"text": text, "reply_markup": {"inline_keyboard": inline_keyboard}}
#         return message

#     def _run_callback_query_(self) -> HttpResponse:
#         if self.next_state.name == States.UNIDF_welcome.name:
#             message = self.next_state._get_message_()
#             data = {"chat_id": self.handler.chat_id}
#             data.update(message)
#             self._message_("send", data)
#             data = {
#                 "chat_id": self.handler.chat_id,
#                 "message_id": self.handler.data["message"]["message_id"],
#             }
#             self._message_("delete", data)
#             return HttpResponse("ok")
#         elif self.next_state.name in [
#             States.UNIDF_edit_info_name.name,
#             States.UNIDF_edit_info_grade.name,
#             States.UNIDF_edit_info_phone_number.name,
#         ]:
#             next_message = self.next_state._get_message_()
#             data = {"chat_id": self.handler.chat_id, **next_message}
#             self._message_("send", data)

#             user_state_message = {"update": self.handler.data["message"]["message_id"]}
#             user_state_message.update({"delete": self.sent_message_id})
#             user_state_message = json.dumps(user_state_message)

#             self.handler.user_state.message_ids = user_state_message
#             self.handler.user_state.save()

#             return HttpResponse("ok")

#         self.logger.error("_run_callback_query_ did not recognize the next state")
#         return HttpResponse("Not ok")


# class BaseInputState(BaseState):
#     model: Model

#     def __init__(self, handler) -> None:
#         super().__init__(handler)
#         self.expected_inputs.append(self.MESSAGE)

#     def _run_callback_query_(self) -> HttpResponse:
#         next_state_obj = getattr(States, States.UNIDF_edit_info.name)
#         self.next_state = next_state_obj(self.handler)

#         try:
#             self.next_state_model = bot_models.State.objects.get(
#                 name=self.next_state.name
#             )
#         except ObjectDoesNotExist as e:
#             msg = f"next state model does not exist\n"
#             msg += f"{self.handler.data=}"
#             self.logger.error(msg=msg)
#             return HttpResponse("error")
#         else:
#             next_message = self.next_state._get_message_()
#             message_ids = self.handler.user_state.message_ids
#             message_ids = json.loads(message_ids)
#             # self.logger.error(message_ids)

#             data = {
#                 "chat_id": self.handler.chat_id,
#                 "message_id": message_ids["delete"],
#             }
#             self._message_("delete", data)

#             data = {
#                 "chat_id": self.handler.chat_id,
#                 "message_id": message_ids["update"],
#                 **next_message,
#             }
#             self._message_("update", data)

#             data = {
#                 "chat_id": self.handler.chat_id,
#                 "message_id": self.handler.data["message"]["message_id"],
#             }
#             self._message_("delete", data)

#             return HttpResponse("ok")

#     def _run_message_(self) -> HttpResponse:
#         next_state_obj = getattr(States, States.UNIDF_edit_info.name)
#         self.next_state = next_state_obj(self.handler)

#         try:
#             self.next_state_model = bot_models.State.objects.get(
#                 name=self.next_state.name
#             )
#         except ObjectDoesNotExist as e:
#             msg = f"next state model does not exist\n"
#             msg += f"{self.handler.data=}"
#             self.logger.error(msg=msg)
#             return HttpResponse("error")
#         else:
#             next_message = self.next_state._get_message_()
#             message_ids = self.handler.user_state.message_ids
#             message_ids = json.loads(message_ids)
#             # self.logger.error(message_ids)

#             data = {
#                 "chat_id": self.handler.chat_id,
#                 "message_id": message_ids["delete"],
#             }
#             self._message_("delete", data)

#             data = {
#                 "chat_id": self.handler.chat_id,
#                 "message_id": message_ids["update"],
#                 **next_message,
#             }
#             self._message_("update", data)

#             data = {
#                 "chat_id": self.handler.chat_id,
#                 "message_id": self.handler.data["message_id"],
#             }
#             self._message_("delete", data)

#             return HttpResponse("ok")


# class UNIDFEditInfoName(BaseInputState):
#     name = "UNIDF_edit_info_name"

#     def __init__(self, handler) -> None:
#         super().__init__(handler)

#     def _get_message_(self) -> dict:
#         return {"text": "Please enter your name"}

#     def _run_message_(self) -> HttpResponse:
#         new_name = self.handler.data["text"]
#         # self.logger.error(f"CUSTOM: {new_name} {self.handler.data}")
#         self.handler.user.name = new_name
#         self.handler.user.save()

#         return super()._run_message_()


# class UNIDFEditInfoPhoneNumber(BaseInputState):
#     name = "UNIDF_edit_info_phone_number"

#     def __init__(self, handler) -> None:
#         super().__init__(handler)

#     def _get_message_(self) -> dict:
#         return {"text": "Please enter your Phone Number"}

#     def _run_message_(self) -> HttpResponse:
#         new_phone_number = self.handler.data["text"]
#         self.handler.user.phone_number = new_phone_number
#         self.handler.user.save()

#         return super()._run_message_()


# class UNIDFEditInfoGrade(BaseInputState):
#     name = "UNIDF_edit_info_grade"

#     def __init__(self, handler) -> None:
#         super().__init__(handler)
#         self.expected_inputs.append(self.CALLBACK_QUERY)
#         self.expected_next_states = [States.UNIDF_edit_info.name]

#     def _get_message_(self) -> dict:
#         grades = eps_models.Student.GRADE_CHOICES
#         inline_keyboard = []
#         for grade in grades:
#             if grade[0] == "UNKWN":
#                 continue
#             text = grade[1]
#             data = grade[0]
#             callback_data = self._create_callback_data_json_(UNIDFEditInfo.name, data)
#             inline_keyboard.append([{"text": text, "callback_data": callback_data}])

#         text = "Please Choose your grade from buttons blow"

#         message = {"text": text, "reply_markup": {"inline_keyboard": inline_keyboard}}

#         return message

#     def _run_callback_query_(self) -> HttpResponse:
#         self.handler.user.student.grade = self.callback_data
#         self.handler.user.student.save()
#         return super()._run_callback_query_()


# class States:
#     UNIDF_welcome = UNIDFWelcome
#     UNIDF_edit_info = UNIDFEditInfo
#     UNIDF_edit_info_name = UNIDFEditInfoName
#     UNIDF_edit_info_phone_number = UNIDFEditInfoPhoneNumber
#     UNIDF_edit_info_grade = UNIDFEditInfoGrade


# class StartCommand(BaseState):
#     def __init__(self, handler) -> None:
#         super().__init__(handler)

#     def handle(self) -> HttpResponse:
#         next_state = States.UNIDF_welcome(self.handler)
#         next_message = next_state._get_message_()
#         data = {"chat_id": self.handler.chat_id, **next_message}
#         self._message_("send", data)
#         try:
#             next_state_model = bot_models.State.objects.get(name=next_state.name)
#         except ObjectDoesNotExist as e:
#             msg = f"state model: start does not exist!"
#             self.logger.error(msg=msg)
#             return HttpResponse(msg)
#         self._set_user_state_(next_state_model)
#         return HttpResponse("ok")


# class Commands:
#     start = StartCommand
