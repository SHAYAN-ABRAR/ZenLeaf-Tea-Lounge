"""ASGI entry point, for servers such as uvicorn."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zenleaf.settings")
application = get_asgi_application()
