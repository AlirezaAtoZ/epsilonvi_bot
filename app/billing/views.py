from typing import Any
from django import http
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.views.generic import RedirectView
from django.conf import settings
from .models import Invoice
from .zarinpal import Zarinpal


class ZarinpalRequestCBV(RedirectView):
    def get_redirect_url(self, *args: Any, **kwargs: Any):
        if settings.ZP_SANDBOX:
            sandbox = 'sandbox'
        else:
            sandbox = 'www'
        # make request to zarinpal
        zp_request = f"https://{sandbox}.zarinpal.com/pg/rest/WebGate/PaymentRequest.json"
        invoice = Invoice.objects.filter(pk=self.kwargs["pk"]).first()
        if invoice:
            zarinpal = Zarinpal(invoice)
            url = zarinpal.get_payment_gateway()
            self.url = url
        else:
            self.url = "https://epsilonvi.ir/dev/"
        return super().get_redirect_url(*args, **kwargs)


class ZarinpalVerifyCBV(RedirectView):
    def get_redirect_url(self, *args: Any, **kwargs: Any):
        pk = self.kwargs.get("pk", None)
        if pk:
            invoice = Invoice.objects.filter(pk=pk).first()
            if invoice:
                zp = Zarinpal(invoice)
                url = zp.get_telegram_url()
                self.url = url
            else:
                self.url = f"https://t.me/{settings.BOT_USERNAME}?start=action_verify_0"
        return super().get_redirect_url(*args, **kwargs)
