"""WSGI entry point, used by production servers such as gunicorn or waitress."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zenleaf.settings")
application = get_wsgi_application()
