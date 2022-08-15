from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EventConfig(AppConfig):
    name = "atlima_django.sport_events"
    verbose_name = _("Sport Events in Atlima")
