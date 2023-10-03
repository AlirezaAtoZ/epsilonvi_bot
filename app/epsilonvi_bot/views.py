from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json
import os
from bot import models as bot_models
from user import models as user_models
from .handlers import Handlers


# TODO put it in utils
def to_camel_case(string):
    return ''.join(word.capitalize() for word in string.split('_'))


@csrf_exempt
def webhook(request):
    # check the sender is telegram
    if not 'X-Telegram-Bot-Api-Secret-Token' in request.headers:
        return HttpResponseForbidden('no secret token was provided.')
    elif os.environ.get('EPSILONVI_DEV_SECRET_TOKEN') == request.META.get('EPSILONVI_DEV_SECRET_TOKEN'):
        return HttpResponseBadRequest('secrect token not matched.')
    data = json.loads(request.body)

    # get request type
    REQUEST_TYPES = [
        'message', 'edited_message',
        'channel_post', 'edited_channel_post',
        'inline_query', 'chosen_inline_result',
        'callback_query',
        'shipping_query', 'pre_checkout_query',
        'poll', 'poll_answer',
        'my_chat_member', 'chat_member', 'chat_join_request'
    ]

    for request_type in REQUEST_TYPES:
        if request_type in data:
            handler_obj = getattr(Handlers, request_type)
            handler = handler_obj(data)
            break
    else:
        handler_obj = getattr(Handlers, 'other')
        handler = handler_obj(data)
    
    # from handlers import BaseHandler
    # handler = BaseHandler()
    # if handler.is_done():
    #     return HttpResponse('already processed the request.')

    # get or create user
    # telegram_id = handler.get_telegram_id()
    # user, created = user_models.User.objects.get_or_create(
    #     telegram_id=telegram_id)
    # if created:
    #     user.name = handler.get_telegram_name()
    #     user.save()
    
    return handler.handle()
