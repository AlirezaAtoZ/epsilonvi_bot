from bot import utils
from conversation import models
from epsilonvi_bot import permissions as perm
from epsilonvi_bot.models import Student, Teacher, Admin


class ConversationStateHandler:
    _conv: models.Conversation

    NEW_QUESTION_TEXT = "سوال جدید /start"
    NEW_ANSWER_TEXT = "پاسخ جدید /start"
    NEW_REQUESTION_TEXT = "اعتراض به پاسخ دبیر /start"

    MORE_INFO_FORMAT = "مشاهده جزییات: {}"

    STDNT_QUESTION_ANSWERED_FORMAT = "پرسش {} پاسخ داده شد.\n"
    STDNT_RE_QUESTION_DENIED_FORMAT = (
        "اعتراض شما به پاسخ دبیر در مکالمه {} توسط ادمین رد شد.\n"
    )
    STDNT_QUESTION_DENIED = "پرسش شما توسط ادمین رد شد.\n"

    TCHER_ANSWER_DENIED_FORMAT = "پاسخ شما به پرسش {} توسط ادمین قبول نشد\n"
    TCHER_RE_QUESTIONED_FORMAT = "دانش آموز به پاسخ شما در مکالمه {} اعتراض کرده است و ادمین این اعتراض را تایید کرده است\n"

    ACTION_NOT_FOUND_TEXT = "action not found"

    def __init__(self, conversation: models.Conversation) -> None:
        self._conv = conversation

    def __result_dict(self, result: bool, description=None):
        _dict = {"result": result, "description": description}
        return _dict

    def __get_admins_query(self, *permissions):
        _q = Admin.objects.filter(is_active=True)
        for p in permissions:
            _q = _q.filter(permissions__contains=p.name)
        return _q

    def __get_users_from_admins(self, admins_query):
        users = []
        for admin in admins_query:
            users.append(admin.user)
        return users

    def __get_users_from_teachers(self, teachers_query):
        users = []
        for teacher in teachers_query:
            users.append(teacher.user)
        return users

    def _handle_q_stdnt_drft(self, action=None):
        # increase asked questions of the package
        check = self._conv.student_package.increase_asked()
        if check:
            # send notification to all corresponding adimns
            admins = self.__get_admins_query(perm.IsAdmin, perm.CanApproveConversation)
            users = self.__get_users_from_admins(admins)
            self._conv.student_package.save()
            utils.send_group_message({"text": self.NEW_QUESTION_TEXT}, users)
            # set the next state
            self._conv.conversation_state = "Q-STDNT-COMP"
            self._conv.save()
            return self.__result_dict(True, "ok")
        else:
            return self.__result_dict(False, "not enough questions left in the package")

    def _handle_q_stdnt_comp(self, action=None):
        if action == "approve":
            subject = self._conv.subject
            next_state_name = "Q-ADMIN-APPR"
            # send notification to all corresponding teachers
            teachers = subject.teacher_set.filter(is_active=True)
            if teachers.exists():
                users = self.__get_users_from_teachers(teachers)
                utils.send_group_message({"text": self.NEW_QUESTION_TEXT}, users)
                self._conv.conversation_state = next_state_name
                self._conv.save()
                return self.__result_dict(True, "ok")

            else:
                admins = self.__get_admins_query(perm.IsAdmin, perm.AddAdmin)
                users = self.__get_users_from_admins(admins)
                text = (
                    f"سوال با درس {subject} مطرح شده اما دبیری مطابق این درس یافت نشد."
                )
                utils.send_group_message({"text": text}, users)
                self._conv.conversation_state = next_state_name
                self._conv.save()
                return self.__result_dict(True, "ok")

        elif action == "deny":
            next_state_name = "Q-ADMIN-DENY"
            self._conv.conversation_state = next_state_name
            self._conv.save()
            return self.__result_dict(True, "ok")
        else:
            return self.__result_dict(False, "action not found")

    def _handle_q_admin_appr(self, action=None):
        self._conv.conversation_state = "A-TCHER-DRFT"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_q_admin_deny(self, action=None):
        self._conv.conversation_state = "Q-ADMIN-DRFT"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_q_admin_drft(self, action=None):
        # send notification to the student
        student = self._conv.student
        text = self.STDNT_QUESTION_DENIED
        text += self.MORE_INFO_FORMAT.format(self._conv.get_telegram_command())
        utils.send_group_message({"text": text}, [student.user])
        # set the next state and denied status
        self._conv.student_denied = True
        self._conv.conversation_state = "Q-ADMIN-COMP"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_q_admin_comp(self, action=None):
        # set the next state
        self._conv.conversation_state = "Q-STDNT-DEND"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_q_stdnt_dend(self, action=None):
        # set the next state and denied status
        self._conv.conversation_state = "Q-STDNT-DRFT"
        self._conv.student_denied = False
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_a_tcher_drft(self, action=None):
        # send notification to all corresponding admins
        admins = self.__get_admins_query(perm.IsAdmin, perm.CanApproveConversation)
        users = self.__get_users_from_admins(admins)
        self._conv.student_package.save()
        utils.send_group_message({"text": self.NEW_ANSWER_TEXT}, users)
        # set the next state
        self._conv.conversation_state = "A-TCHER-COMP"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_a_tcher_comp(self, action=None):
        if action == "approve":
            # send notification to the student
            student = self._conv.student
            text = self.STDNT_QUESTION_ANSWERED_FORMAT.format(
                self._conv.get_telegram_command()
            )
            utils.send_group_message({"text": text}, [student.user])
            # set the next state
            next_state_name = "A-ADMIN-APPR"
            self._conv.conversation_state = next_state_name
            self._conv.save()
            return self.__result_dict(True, "ok")
        elif action == "deny":
            next_state_name = "A-ADMIN-DENY"
            self._conv.conversation_state = next_state_name
            self._conv.save()
            return self.__result_dict(True, "ok")
        else:
            return self.__result_dict(False, "action not found")

    def _handle_a_admin_appr(self, action=None):
        if action == "approve":
            # set the next state
            next_state_name = "A-STDNT-APPR"
            self._conv.conversation_state = next_state_name
            self._conv.save()

            return self.__result_dict(True, "ok")
        elif action == "deny":
            next_state_name = "A-STDNT-DENY"
            self._conv.conversation_state = next_state_name
            self._conv.save()
            return self.__result_dict(True, "ok")
        else:
            return self.__result_dict(False, "action not found")

    def _handle_a_admin_deny(self, action=None):
        self._conv.conversation_state = "A-ADMIN-DRFT"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_a_admin_drft(self, action=None):
        # send notification to the teacher
        teacher = self._conv.teacher
        text = self.TCHER_ANSWER_DENIED_FORMAT.format(self._conv.get_telegram_command())
        text += self.MORE_INFO_FORMAT.format(self._conv.get_telegram_command())
        utils.send_group_message({"text": text}, [teacher.user])
        # set the next state and denied status
        self._conv.conversation_state = "A-TCHER-COMP"
        self._conv.teacher_denied = True
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_a_admin_comp(self, action=None):
        # set the next state
        self._conv.conversation_state = "A-TCHER-DEND"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_a_tcher_dend(self, action=None):
        self._conv.conversation_state = "A-TCHER-DRFT"
        self._conv.teacher_denied = False
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_a_stdnt_appr(self, action=None):
        self._conv.conversation_state = "C-CONVR-DONE"
        self._conv.is_done = True
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_a_stdnt_deny(self, action=None):
        self._conv.conversation_state = "RQ-STDNT-DRFT"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_rq_stdnt_drft(self, action=None):
        # send notification to all corresponding admins
        admins = self.__get_admins_query(perm.IsAdmin, perm.CanApproveConversation)
        users = self.__get_users_from_admins(admins)
        utils.send_group_message({"text": self.NEW_REQUESTION_TEXT}, users)
        # set the next state
        self._conv.conversation_state = "RQ-STDNT-COMP"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_rq_stdnt_comp(self, action=None):
        if action == "approve":
            # set the next state
            self._conv.conversation_state = "RQ-ADMIN-APPR"
            self._conv.save()
            # send notification to the teacher
            teacher = self._conv.teacher
            text = self.TCHER_RE_QUESTIONED_FORMAT.format(
                self._conv.get_telegram_command()
            )
            text += self.MORE_INFO_FORMAT.format(self._conv.get_telegram_command())
            utils.send_group_message({"text": text}, [teacher.user])
            return self.__result_dict(True, "ok")
        elif action == "deny":
            # set next state
            self._conv.conversation_state = "RQ-ADMIN-DENY"
            self._conv.save()
            return self.__result_dict(True, "ok")
        else:
            return self.__result_dict(False, "action not found")

    def _handle_rq_admin_appr(self, action=None):
        self._conv.conversation_state = "RA-TCHER-DRFT"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_rq_admin_deny(self, action=None):
        self._conv.conversation_state = "RQ-ADMIN-DRFT"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_rq_admin_drft(self, action=None):
        # send notification to the student
        student = self._conv.student
        text = self.STDNT_RE_QUESTION_DENIED_FORMAT.format(
            self._conv.get_telegram_command()
        )
        text += self.MORE_INFO_FORMAT.format(self._conv.get_telegram_command())
        utils.send_group_message({"text": text}, [student.user])
        # set the next state
        self._conv.conversation_state = "RQ-ADMIN-COMP"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_rq_admin_comp(self, action=None):
        # set the next state
        self._conv.conversation_state = "RQ-STDNT-DEND"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_rq_stdnt_dend(self, action=None):
        self._conv.conversation_state = "C-CONVR-DONE"
        self._conv.is_done = True
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_ra_tcher_drft(self, action=None):
        # send notification to all corresponding admins
        admins = self.__get_admins_query(perm.IsAdmin, perm.CanApproveConversation)
        users = self.__get_users_from_admins(admins)
        utils.send_group_message({"text": self.NEW_ANSWER_TEXT}, users)
        # set the next state
        self._conv.conversation_state = "RA-TCHER-COMP"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_ra_tcher_comp(self, action=None):
        if action == "approve":
            # set the next state
            next_state_name = "RA-ADMIN-APPR"
            self._conv.conversation_state = next_state_name
            self._conv.save()
            # send notification to the student
            student = self._conv.student
            text = self.STDNT_QUESTION_ANSWERED_FORMAT.format(
                self._conv.get_telegram_command()
            )
            utils.send_group_message({"text": text}, [student.user])
            return self.__result_dict(True, "ok")
        elif action == "deny":
            next_state_name = "RA-ADMIN-DENY"
            self._conv.conversation_state = next_state_name
            self._conv.save()
            return self.__result_dict(True, "ok")
        else:
            return self.__result_dict(False, self.ACTION_NOT_FOUND_TEXT)

    def _handle_ra_admin_appr(self, action=None):
        # set the next state
        self._conv.conversation_state = "RA-STNDT-APPR"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_ra_stdnt_appr(self, action=None):
        self._conv.conversation_state = "C-CONVR-DONE"
        self._conv.is_done = True
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_ra_admin_deny(self, action=None):
        self._conv.conversation_state = "RA-ADMIN-DRFT"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_ra_admin_drft(self, action=None):
        # send notification to the teacher
        teacher = self._conv.teacher
        text = self.TCHER_ANSWER_DENIED_FORMAT.format(self._conv.get_telegram_command())
        text += self.MORE_INFO_FORMAT.format(self._conv.get_telegram_command())
        utils.send_group_message({"text": text}, [teacher.user])
        # set the next state and denied status
        self._conv.conversation_state = "RA-ADMIN-COMP"
        self._conv.teacher_denied = True
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_ra_admin_comp(self, action=None):
        # set the next state
        self._conv.conversation_state = "RA-TCHER-DEND"
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_ra_tcher_dend(self, action=None):
        self._conv.conversation_state = "RA-TCHER-DRFT"
        self._conv.teacher_denied = False
        self._conv.save()
        return self.__result_dict(True, "ok")

    def _handle_c_convr_done(self, action=None):
        return self.__result_dict(True, "what is dead may never die")

    def is_waiting_on_admin(self):
        _cs = self._conv.conversation_state
        _true_states = [
            "Q-STDNT-COMP",
            "RQ-STDNT-COMP",
            "A-TCHER-COMP",
            "RA-TCHER-COMP",
        ]
        if _cs in _true_states:
            return True
        else:
            return False

    def is_waiting_on_student(self):
        _true_states = ["A-ADMIN-APPR", "Q-STDNT-DEND", "RQ-STNDT-DRFT"]
        if self._conv.conversation_state in _true_states:
            return True
        else:
            return False

    def is_student_denied(self):
        _true_states = ["Q-STDNT-DEND"]
        if self._conv.conversation_state in _true_states:
            return True
        else:
            return False

    def is_waiting_on_teacher(self):
        _true_states = [
            "Q-ADMIN-APPR",
            "RQ-ADMIN-APPR",
            "A-TCHER-DEND",
            "RA-TCHER-DEND",
            "A-TCHER-DRFT",
            "RA-TCHER-DRFT",
        ]
        if self._conv.conversation_state in _true_states:
            return True
        else:
            return False

    def is_waiting_new_teacher(self):
        if (
            self._conv.conversation_state == "Q-ADMIN-APPR"
            and self._conv.teacher == None
        ):
            return True
        return False

    def is_waiting_denied(self):
        _true_states = ["A-TCHER-DEND"]
        if self._conv.conversation_state in _true_states:
            return True
        else:
            return False

    def handle(self, action=None):
        _conv_state = self._conv.conversation_state
        _low = str(_conv_state).lower()
        _meth_name = str(_low).replace("-", "_")
        method = getattr(self, f"_handle_{_meth_name}")
        return method(action)
