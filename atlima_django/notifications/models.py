from django.db import models
from atlima_django.system.models import (SystemObject, 
                                         SystemEvent, 
                                         SystemEventType)
from atlima_django.users.models import User
from parler.models import TranslatableModel, TranslatedFields

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
        text=models.TextField()
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



class Notification(models.Model):
    """
    Notification model: build in serializer
    from notification template, prepared
    in admin panel
    """

    is_readed = models.BooleanField(
        default=False,
        verbose_name="User has read notification",
    )
    atlima_obj_type = models.ForeignKey(
        to=SystemObject,
        on_delete=models.CASCADE,
        related_name="sender_model",
        null=True,
    )
    atlima_obj_id = models.IntegerField(
        null=True,
        blank=True
    )
    target_user = models.ForeignKey(
        to=User,
        verbose_name="User",
        on_delete=models.CASCADE,
    )

    # системное событие, ставшее источником уведомления
    system_event = models.ForeignKey(
        to=SystemEvent,
        on_delete=models.CASCADE,
        related_name="system_event_notify",
        null=True,
        blank=True
    )
    # ссылка на шаблон текста уведомления
    notification_template = models.ForeignKey(
        to=NotificationTemplate,
        on_delete=models.CASCADE,
        related_name="template_used",
        null=True,
        blank=True
    )

    # Meta
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.target_user.username
    
