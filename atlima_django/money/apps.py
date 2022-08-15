from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MoneyConfig(AppConfig):
    name = "atlima_django.money"
    verbose_name = _("Money")
