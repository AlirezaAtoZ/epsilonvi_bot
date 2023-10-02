from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json
import os
from bot import models as bot_models
from user import models as user_models


def to_camel_case(string):
    return ''.join(word.capitalize() for word in string.split('_'))


@csrf_exempt
def webhook(request):
    # check the sender is telegram
    if not hasattr(request.META, 'X-Telegram-Bot-Api-Secret-Token'):
        return HttpResponseForbidden()
    elif os.environ.get('EPSILONVI_DEV_SECRET_TOKEN') == request.META.get('EPSILONVI_DEV_SECRET_TOKEN'):
        return HttpResponseBadRequest()
    data = json.loads(request.body)


    # check if the request is new
    update_id = data['update_id']
    query = bot_models.UpdateID.objects.filter(update_id=update_id)
    if query.exists():
        if query[0].is_done:
            return HttpResponse('already processed the request')
    


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
    handlers = [MessageHandler, CallbackQueryHandler, OtherHandler]

    for request_type in REQUEST_TYPES:
        if hasattr(data, request_type):
            handler_obj = getattr(
                handlers,
                f'{to_camel_case(request_type)}Handler',
                OtherHandler)
            handler = handler_obj(data[request_type])
    

    # get or create user
    telegram_id = handler.get_telegram_id()
    user, created = user_models.User.objects.get_or_create(telegram_id=telegram_id)
    if created:
        user.name = handler.get_telegram_name()
        user.save()
    

    

    
    return HttpResponse()


class BaseHandler:
    def __init__(self, data) -> None:
        self.data
    

    def get_telegram_id(self):
        telegram_id = self.data['from']['id']
        return str(telegram_id)
    
    def get_telegram_name(self):
        telegram_name = self.data['from']['first_name']
        return str(telegram_name)

class MessageHandler(BaseHandler):
    pass


class CallbackQueryHandler(BaseHandler):
    pass


class OtherHandler(BaseHandler):
    pass
