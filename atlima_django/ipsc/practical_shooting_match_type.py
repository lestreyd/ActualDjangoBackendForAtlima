from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class PracticalShootingMatchType(models.Model):
    """property for event""" ""

    translatable = TranslatedFields(
        title=models.CharField(max_length=255),
        description=models.CharField(max_length=255),
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = str(self.pk)
        return f"PropertyIPSC id{sid}"
