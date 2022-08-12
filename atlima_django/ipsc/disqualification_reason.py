from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class DisqualificationReason(TranslatableModel):
    """Модель причин дисквалификации"""
    title = TranslatedFields(text=models.CharField(max_length=255))
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = str(self.id)
        return f"Disqualification {sid}"

