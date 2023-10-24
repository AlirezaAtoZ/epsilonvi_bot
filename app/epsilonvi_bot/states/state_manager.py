import logging
import traceback

from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from bot import models as bot_models
from epsilonvi_bot import models as eps_models
from user import models as usr_models
from epsilonvi_bot.states import admin, teacher, student


class StateManager(object):
    state_mapping = {
        "STDNT_error": student.StudentError,
        "STDNT_home": student.StudentHome,
        "STDNT_package_manager": student.StudentPackageManager,
        "STDNT_package_history": student.StudentPackageHistory,
        "STDNT_question_manager": student.StudentQuestionManager,
        student.StudentPackageAdd.name: student.StudentPackageAdd,
        student.StudentPackageConfirm.name: student.StudentPackageConfirm,
        "STDNT_new_question_choose": student.StudentNewQuestionChoose,
        "STDNT_new_question_confirm": student.StudentNewQuestionChoose,
        student.StudentQuestionAdd.name: student.StudentQuestionAdd,
        student.StudentQuestionCompose.name: student.StudentQuestionCompose,
        student.StudentQuestionConfirm.name: student.StudentQuestionConfirm,
        "STDNT_question_history": student.StudentQuestionHistory,
        "STDNT_edit_info": student.StudentEditInfo,
        "STDNT_edit_info_name": student.StudentEditInfoName,
        "STDNT_edit_info_phone_number": student.StudentEditInfoPhoneNumber,
        student.StudentEditInfoGrade.name: student.StudentEditInfoGrade,
        admin.AdminHome.name: admin.AdminHome,
        admin.AdminSendGroupMessage.name: admin.AdminSendGroupMessage,
        admin.AdminSendGroupMessageConfirm.name: admin.AdminSendGroupMessageConfirm,
        admin.AdminAdminManager.name: admin.AdminAdminManager,
        admin.AdminAdminAdd.name: admin.AdminAdminAdd,
        admin.AdminAdminList.name: admin.AdminAdminList,
        admin.AdminAdminDetail.name: admin.AdminAdminDetail,
        admin.AdminQuestionManager.name: admin.AdminQuestionManager,
        admin.AdminQuestionList.name: admin.AdminQuestionList,
        admin.AdminQuestionDetail.name: admin.AdminQuestionDetail,
        admin.AdminQuestionDeny.name: admin.AdminQuestionDeny,
        admin.AdminTeacherManager.name: admin.AdminTeacherManager,
        admin.AdminTeacherAdd.name: admin.AdminTeacherAdd,
        admin.AdminTeacherList.name: admin.AdminTeacherList,
        admin.AdminTeacherDetail.name: admin.AdminTeacherDetail,
        admin.AdminInfoManager.name: admin.AdminInfoManager,
        admin.AdminInfoName.name: admin.AdminInfoName,
        admin.AdminInfoPhoneNumber.name: admin.AdminInfoPhoneNumber,
        admin.AdminInfoCreditCardNumber.name: admin.AdminInfoCreditCardNumber,
        teacher.TeacherHome.name: teacher.TeacherHome,
        teacher.TeacherInfoManager.name: teacher.TeacherInfoManager,
        teacher.TeacherInfoName.name: teacher.TeacherInfoName,
        teacher.TeacherInfoPhoneNumber.name: teacher.TeacherInfoPhoneNumber,
        teacher.TeacherInfoCreditCard.name: teacher.TeacherInfoCreditCard,
    }

    def __init__(self, telegram_response_body) -> None:
        self.logger = logging.getLogger(__name__)
        self._tlg_res = telegram_response_body
        self.telegram_id = None
        self.current_state = None

    def _get_error_prefix(self):
        return "[CUSTOM ERROR] [STATE MANAGER]:\t"

    def _get_or_create_user(self):
        if "callback_query" in self._tlg_res.keys():
            _from = self._tlg_res["callback_query"]["from"]
        else:
            _from = self._tlg_res["message"]["from"]

        self.telegram_id = _from["id"]
        try:
            user, is_new = usr_models.User.objects.get_or_create(
                telegram_id=self.telegram_id
            )
            if is_new:
                user.name = _from["first_name"]
                user.save()
                _ = eps_models.Student.objects.create(user=user)
                state = bot_models.State.objects.get(name="STDNT_home")
                _ = bot_models.UserState.objects.create(user=user, state=state)
        except ObjectDoesNotExist as err:
            msg = self._get_error_prefix()
            msg += f"DoesNotExist _get_or_create_user\t{_from=}"
            self.logger.error(msg=msg)
            user = is_new = None
        except Exception as err:
            msg = self._get_error_prefix()
            msg += f"_get_or_create_user\t{_from=} {err=}"
            self.logger.error(msg=msg)
            user = is_new = None
        return user, is_new

    def handle(self) -> HttpResponse:
        user, _ = self._get_or_create_user()
        if user:
            try:
                user_state = bot_models.UserState.objects.get(user=user)
                self.current_state = self.state_mapping[user_state.state.name]
            except ObjectDoesNotExist as err:
                msg = self._get_error_prefix()
                msg += f"DoesNotExist handle\t {user=}"
                self.logger.error(msg=msg)
                self.current_state = self.state_mapping["STDNT_error"]
            except Exception as err:
                msg = self._get_error_prefix()
                msg += f"handle\t {err=}"
                self.logger.error(msg=msg)
                self.current_state = self.state_mapping["STDNT_error"]
        else:
            msg = self._get_error_prefix()
            msg += f"else user\t{self._tlg_res}"
            self.logger.error(msg=msg)
            return HttpResponse("Something went wrong")

        # self.logger.error(f"state handler {user}")
        # TODO do it with RAM
        if user.lock:
            return HttpResponse()
        else:
            try:
                user.lock = True
                user.save()
                http_response = self.current_state(self._tlg_res, user).handle()
            except:
                self.logger.error(traceback.print_exc())
                return HttpResponse()
            finally:
                user.lock = False
                user.save()
        return http_response
