from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LocationConfig(AppConfig):
    name = "atlima_django.location"
    verbose_name = _("Location")
