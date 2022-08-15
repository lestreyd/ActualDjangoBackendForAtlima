from django.db import models
from atlima_django.users.models import User
from parler.models import TranslatedFields, TranslatableModel


class SystemObject(models.Model):
    """Representation of objects in system"""

    title = models.CharField(
        max_length=128,
        unique=True,
        verbose_name="Title",
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class SystemEventType(models.Model):
    """Type of system event"""

    title = models.CharField(
        max_length=256,
        unique=True,
        verbose_name="title",
    )
    description = models.CharField(
        max_length=512, verbose_name="description"
    )
    system_object = models.ForeignKey(
        to=SystemObject,
        on_delete=models.CASCADE,
        related_name="system_object_for_event_type",
        null=True,
        blank=True,
        verbose_name="System object",
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class SystemEvent(models.Model):
    """Модель для хранения системных событий"""

    created = models.DateTimeField(
        auto_now_add=True
    )
    user = models.ForeignKey(
        to=User, on_delete=models.CASCADE
    )
    system_type = models.ForeignKey(
        to=SystemEventType,
        on_delete=models.CASCADE,
    )
    json_attributes = models.JSONField(
        null=True, blank=True
    )

    def __str__(self):
        return f"{self.user.username}_{str(self.created)}"


class UserAgreement(TranslatableModel):
    """
    User Agreement model with content, title
    and description fields in content field
    """
    document_version = models.IntegerField(
        null=False, blank=False
    )
    slug = models.SlugField(
        max_length=64, unique=True
    )
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now=True)
    content = TranslatedFields(
        text=models.TextField()
    )

    def __str__(self):
        return (
            f"{self.pk}_{self.document_version}"
        )
