import json
import logging
import requests
from django.utils import timezone
from django.conf import settings
from .models import Invoice


class Zarinpal(object):
    def __init__(self, invoice: Invoice = None) -> None:
        self.invoice = invoice
        if settings.ZP_SANDBOX:
            sandbox = "sandbox"
        else:
            sandbox = "www"
        self.payment_request_url = (
            f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
        )
        self.start_pay_url = f"https://{sandbox}.zarinpal.com/pg/StartPay/"
        self.payment_verification_url = (
            f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentVerification.json"
        )

    def get_payment_gateway(self):
        self.invoice.set_callback_url()
        _dict = {
            "MerchantID": settings.ZP_MERCHANT_ID,
            "Amount": self.invoice.amount,
            "Description": self.invoice.description,
            "CallbackURL": self.invoice.callback_url,
        }
        data = json.dumps(_dict)

        headers = {"content-type": "application/json", "content-length": str(len(data))}

        response = requests.post(
            url=self.payment_request_url, data=data, headers=headers, timeout=10
        )

        if response.status_code == 200:
            res = response.json()
            self.invoice.authority = str(res["Authority"])
            pay_url = self.start_pay_url + str(int(self.invoice.authority))
            self.invoice.payment_url = pay_url
            self.invoice.is_pending = True
            self.invoice.save()
            self.invoice.student_package.is_pending=True
            self.invoice.student_package.save()

        else:
            pass
        return pay_url

    def get_telegram_url(self):
        logger = logging.getLogger(__name__)
        logger.error(f"get_telegram_url has called")
        _dict = {
            "MerchantID": settings.ZP_MERCHANT_ID,
            "Amount": self.invoice.amount,
            "Authority": self.invoice.authority,
        }
        data = json.dumps(_dict)
        headers = {"content-type": "application/json", "content-length": str(len(data))}

        response = requests.post(
            url=self.payment_verification_url, data=data, headers=headers, timeout=10
        )
        logger.error(f"{data=}")
        logger.error(f"{response.json()=}")
        if response.status_code == 200:
            res = response.json()
            if res["Status"] == 100:
                self.invoice.is_paid = True
                self.invoice.status = res["Status"]
                self.invoice.ref_id = res["RefID"]
                self.invoice.paid_date = timezone.now()
                self.invoice.is_pending = False
                self.invoice.save()
                self.invoice.student_package.is_paid = True
                self.invoice.student_package.is_pending = False
                self.invoice.student_package.save()
            else:
                self.invoice.status = res["Status"]
                self.invoice.is_pending = False
                self.invoice.save()   
                self.invoice.student_package.is_pending = False
                self.invoice.student_package.save()             
        return self.invoice.get_verify_telegram_url()
