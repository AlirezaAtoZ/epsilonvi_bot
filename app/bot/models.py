from django.db import models
from user import models as user_models


class File(models.Model):
    file_id = models.TextField()
    file_unique_id = models.TextField()

    FILE_TYPES = [
        ('PHO', 'photo'),
        ('VID', 'video'),
        ('VOC', 'voice'),
        ('DOC', 'document'),
        ('VDM', 'video_note'),]
    file_type = models.CharField(
        max_length=3, choices=FILE_TYPES,
        default='PHO')
    

class UpdateID(models.Model):
    """
    The UpdateID is ued to avoid processing the same
    request more than once.
    """
    update_id = models.BigIntegerField(unique=True)
    is_done = models.BooleanField(default=False)
    datetime = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.datetime)


class Message(models.Model):
    message_id = models.BigIntegerField()
    chat_id = models.BigIntegerField()
    from_id = models.ForeignKey(
        "user.User", on_delete=models.DO_NOTHING,
        blank=True, null=True)
    date = models.DateTimeField()

    # The reason why not using foreign key type here is because
    # thee parent messages may not be in the database
    reply_to_message_id = models.BigIntegerField(blank=True, null=True)
    
    text = models.TextField(blank=True, null=True)
    caption = models.TextField(blank=True, null=True)

    MESSAGE_TYPES = [
        ('TXT', 'text'),
        ('PHO', 'photo'),
        ('VID', 'video'),
        ('VOC', 'voice'),
        ('DOC', 'document'),
        ('VDM', 'video_note'),]
    message_type = models.CharField(
        max_length=3, choices=MESSAGE_TYPES,
        default='TXT')
    
    files = models.ManyToManyField(
        "File", blank=True)
    

    def __str__(self) -> str:
        output = str(self.message_type) + " "
        if self.text: output += str(self.text)
        elif self.caption: output += str(self.caption)
        else: output += "no text provided"
        return output


class StateMessage(models.Model):
    text = None


class StateInlineKeyboard(models.Model):
    layout = None


class State(models.Model):
    name = models.CharField(max_length=64, unique=True)
    # only when input is the keyboard
    next_state = models.ForeignKey("State", on_delete=models.DO_NOTHING, null=True, blank=True)
    message = models.ForeignKey("StateMessage", on_delete=models.DO_NOTHING, null=True, blank=True)
    inline_keyboard = models.ForeignKey("StateInlineKeyboard",  on_delete=models.DO_NOTHING, null=True, blank=True)
    ROLES = [
        ('UNIDF', 'unidentified'),
        ('ADMIN', 'admin'),
        ('SUADM', 'super admin'),
        ('TCHER', 'teacher'),
        ('STDNT', 'student'),
    ]
    role = models.CharField(max_length=5, choices=ROLES, default='UNIDF')

    def __str__(self) -> str:
        return f'{self.role} {self.name}'


class UserState(models.Model):
    user = models.ForeignKey(user_models.User, on_delete=models.DO_NOTHING)
    state = models.ForeignKey(State, on_delete=models.DO_NOTHING)
    
