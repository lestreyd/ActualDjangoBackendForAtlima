from django.db import models
from atlima_django.location.country import Country
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatedFields, TranslatableModel


class Region(TranslatableModel):
    # reference to country
    country = models.ForeignKey(
        to=Country,
        on_delete=models.CASCADE,
        related_name="region_country_ref",
    )
    title = TranslatedFields(
        title=models.CharField(max_length=255)
    )

    code = models.CharField(
        max_length=5, null=True, blank=True
    )

    # Meta
    weight = models.SmallIntegerField(
        verbose_name="Region weight in list"
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
