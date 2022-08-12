from django.db import models
from django.utils.translation import gettext_lazy as _
from atlima_django.location.region import Region
from parler.models import TranslatedFields, TranslatableModel


class City(TranslatableModel):
    # reference to region
    region = models.ForeignKey(
        to=Region,
        null=True,
        on_delete=models.CASCADE,
    )

    TranslatedFields(
        title=models.CharField('Title', max_length=255)
    )
    # Meta
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"city id{str(self.id)}"

    class Meta:
        indexes = [
            models.Index(fields=['region', ]),
        ]
