from django.db import models
from atlima_django.users.models import User


class FrontendLog(models.Model):
    """Модель для логирования ошибок с фронта"""

    hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    device_id = models.CharField(max_length=512)
    message = models.TextField(
        null=True, blank=True
    )
    stack_trace = models.TextField(
        null=True, blank=True
    )
    build = models.PositiveBigIntegerField()
    log_date = models.DateTimeField(
        auto_now_add=True
    )
    error_code = models.CharField(
        max_length=100, null=True, blank=True
    )
    date = models.DateField(
        auto_now_add=True, null=True, blank=True
    )
    updated = models.DateTimeField(
        auto_now=True, null=True, blank=True
    )
    counts = models.PositiveIntegerField(
        default=1
    )

    def __str__(self):
        return f"log_entry_{self.id}"


class FrontendTranslation(models.Model):
    """
    Language Package Model for serving translations from Frontend
    Fields:
    - lang_code - "ru" or "en"
    - data      - content in JSON format
    - created   - package creation time
    - updated   - package updating time
    """

    lang_code = models.CharField(
        max_length=5,
        null=False,
        blank=False,
        unique=True,
    )
    data = models.JSONField(
        null=False, blank=False
    )
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now=True)

    def __str__(self):
        return self.lang_code
