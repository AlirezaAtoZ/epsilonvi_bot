from django.test import TestCase

from .models import Message


class MessageTestCase(TestCase):
    def test_emoji_text(self):
        text = "👶👩‍🦰🧑‍🎓🥥🧀🍠🍠🌶🍆🥖"
        # input()
        message = Message.objects.create(text=text, message_id=0, chat_id=0)
        self.assertEqual(message.text, text)
