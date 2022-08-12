from django.db import models
from atlima_django.sport.system import SystemEventType
from parler.models import TranslatedFields, TranslatableModel


class NotificationTemplate(TranslatableModel):
    """A notification template model for
    calculation and building notification
    for user"""

    system_event_type = models.ForeignKey(
        to=SystemEventType,
        on_delete=models.CASCADE,
        related_name="system_event_type"
    )
    content = TranslatedFields(
        content=models.TextField()
    )
    # расшифровка
    description = models.CharField(
        max_length=1024
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.description
