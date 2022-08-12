from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "atlima_django.sport"
    verbose_name = _("Sport")
