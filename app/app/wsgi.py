# import os
# import sys


# sys.path.insert(0, os.path.dirname(__file__))


# def application(environ, start_response):
#     start_response('200 OK', [('Content-Type', 'text/plain')])
#     message = 'It works!  but why the website is not loading?\n'
#     version = 'Python v' + sys.version.split()[0] + '\n'
#     response = '\n'.join([message, version])
#     return [response.encode()]

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

application = get_wsgi_application()