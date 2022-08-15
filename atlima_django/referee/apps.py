from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RefereeConfig(AppConfig):
    name = "atlima_django.referee"
    verbose_name = _("Referee")
