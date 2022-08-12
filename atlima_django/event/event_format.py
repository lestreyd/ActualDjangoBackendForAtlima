from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class EventFormat(TranslatableModel):
    """Event format for representing in event common
    interface"""

    text = TranslatedFields(title=models.CharField('Title', max_length=255))
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = self.pk
        return f"event format id{sid}"
