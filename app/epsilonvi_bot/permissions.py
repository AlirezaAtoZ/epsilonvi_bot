import json
from epsilonvi_bot import models as eps_models
from user import models as usr_models


class PermissionBase:
    name = ""
    text = ""

    def __init__(self) -> None:
        pass

    def has_permission(self, user):
        _p = self._get_admin_permissions(user)
        if _p and (self.name in _p):
            return True
        return False

    def _get_model_premissions(self, user, model):
        if not type(user) == usr_models.User:
            return None
        _q = model.objects.filter(user=user)
        if not _q.exists():
            return None
        model_obj = _q[0]
        _p = model_obj.permissions
        permissions = json.loads(_p)
        return permissions

    def _get_admin_permissions(self, user):
        permissions = self._get_model_premissions(user=user, model=eps_models.Admin)
        return permissions

    def _get_teacher_permissions(self, user):
        permissions = self._get_model_premissions(user=user, model=eps_models.Teacher)
        return permissions


class SendGroupMessage(PermissionBase):
    name = "send_group_message"
    text = ""

    def __init__(self) -> None:
        super().__init__()


class CanApproveConversation(PermissionBase):
    name = "can_approve_conversation"
    text = ""

    def __init__(self) -> None:
        super().__init__()


class AddAdmin(PermissionBase):
    name = "add_admin"
    text = ""

    def __init__(self) -> None:
        super().__init__()


class AddTeacher(PermissionBase):
    name = "add_teacher"
    text = ""

    def __init__(self) -> None:
        super().__init__()


class IsAdmin(PermissionBase):
    name = "is_admin"
    text = ""

    def __init__(self) -> None:
        super().__init__()

    def has_permission(self, user):
        _p = self._get_admin_permissions(user)
        if _p:
            return True
        return False


class IsTeacher(PermissionBase):
    name = "is_teacher"

    def __init__(self) -> None:
        super().__init__()

    def has_permission(self, user):
        _p = self._get_teacher_permissions(user)
        if _p:
            return True
        return False


class CanPayTeacher(PermissionBase):
    name = "can_pay_teacher"
    text = ""

    def __init__(self) -> None:
        super().__init__()


class IsStudent(PermissionBase):
    name = "is_student"

    def __init__(self) -> None:
        super().__init__()

    def has_permission(self, user):
        if (user.student.grade != "UNKWN") and user.phone_number:
            return True
        return False