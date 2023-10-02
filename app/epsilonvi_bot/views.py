from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime


@csrf_exempt
def save_message(request):
    file_name = str(datetime.now()) + '.json'
    if not request.body: 
        return HttpResponseBadRequest()

    with open(file_name, 'w+') as f:
        f.write(str(request.body))
    
    return HttpResponse()
