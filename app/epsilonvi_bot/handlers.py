import os
from . import states
import requests
from datetime import datetime


class BaseHandler:
    user_state: str
    def __init__(self, data) -> None:
        self.data = data
        self.user_telegram_id = self.get_telegram_id()
        self.user_telegram_name = self.get_telegram_name()
        self.user_chat_id = self.get_chat_id()

    def get_telegram_id(self):
        telegram_id = self.data['from']['id']
        return str(telegram_id)

    def get_telegram_name(self):
        telegram_name = self.data['from']['first_name']
        return str(telegram_name)
    
    def get_chat_id(self):
        chat_id = self.data['chat']['id']
        return str(chat_id)
    
    def handle(self):
        pass


class MessageHandler(BaseHandler):
    def __init__(self, data) -> None:
        super().__init__(data)
    
    def handle(self):
        state = states.UNIDFStartState()
        view = state.get_view()
        data = {'chat_id': self.user_chat_id}
        data.update(view)

        url = f'https://api.telegram.org/bot{os.environ.get("EPSILONVI_DEV_BOT_TOKEN")}/sendMessage'
        res = requests.post(url=url, data=data)

        with open(f'{datetime.now()}.json', 'w') as f:
            f.write(res)



class CallbackQueryHandler(BaseHandler):
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
