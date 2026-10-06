"""WSGI entry point (used by production web servers such as Gunicorn)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "netops.settings")

application = get_wsgi_application()
