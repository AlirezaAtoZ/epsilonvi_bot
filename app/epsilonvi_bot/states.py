class BaseState:
    name: str
    expected_inputs: list
    CALLBACK_QUERY = 'callback_query'
    KEYBOARD = 'keyboard'
    COMMAND = 'command'
    def __init__(self) -> None:
        pass

    def next_state(self, input_type, user_input=None):
        pass

    def handle(self):
        pass

    def get_view(self):
        pass


class UNIDFStartState(BaseState):
    name = "UNIDF_start"

    def __init__(self) -> None:
        super().__init__()
        self.expected_inputs = [self.CALLBACK_QUERY]
    
    def get_view(self):
        text = "welcome"
        inline_keyboard = [
            [{'text': "hello world!", "callback_data": 'hello_world'}],
            [{'text': "سلام جهان!", "callback_data": 'hello_world_fa'}]]
        reply_markup = {'inline_keyboard': inline_keyboard}
        return {'text': text, 'reply_markup': reply_markup}


class States:
    UNIDF_start = UNIDFStartState

    
