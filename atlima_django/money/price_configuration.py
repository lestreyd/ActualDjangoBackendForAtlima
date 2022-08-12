from django.db import models
from parler.models import TranslatedFields, TranslatableModel


class PriceConfiguration(TranslatableModel):
    """Price options for events"""

    titles = TranslatedFields(
        title=models.CharField(max_length=255,
                               unique=True)
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
