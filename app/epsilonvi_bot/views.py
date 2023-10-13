from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
# from datetime import datetime
import json
import os
# from bot import models as bot_models
# from user import models as usr_models
from .handlers import HandlerManager


# TODO put it in utils
def to_camel_case(string):
    return "".join(word.capitalize() for word in string.split("_"))


@csrf_exempt
def webhook(request):
    # check the sender is telegram
    if not "X-Telegram-Bot-Api-Secret-Token" in request.headers:
        return HttpResponseForbidden("no secret token was provided.")
    elif os.environ.get("EPSILONVI_DEV_SECRET_TOKEN") == request.META.get(
        "EPSILONVI_DEV_SECRET_TOKEN"
    ):
        return HttpResponseBadRequest("secrect token not matched.")
    data = json.loads(request.body)

    # get request type
    REQUEST_TYPES = [
        "message",
        "edited_message",
        "channel_post",
        "edited_channel_post",
        "inline_query",
        "chosen_inline_result",
        "callback_query",
        "shipping_query",
        "pre_checkout_query",
        "poll",
        "poll_answer",
        "my_chat_member",
        "chat_member",
        "chat_join_request",
    ]

    handler_manager = HandlerManager(data)
    return handler_manager.handle()
