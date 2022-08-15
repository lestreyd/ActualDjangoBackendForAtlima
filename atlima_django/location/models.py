from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatedFields, TranslatableModel


class Country(TranslatableModel):
    # Names
    titles = TranslatedFields(title = models.CharField(max_length=255))

    # Codes
    alpha2 = models.CharField(
        max_length=2, null=False, db_index=True
    )
    alpha3 = models.CharField(
        max_length=3, null=False, db_index=True
    )
    iso = models.SmallIntegerField()

    # Location
    location = models.CharField(
        max_length=128, null=True
    )
    location_precise = models.CharField(
        max_length=256, null=True
    )

    # Ordering
    weight_in_list = models.SmallIntegerField()

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    # Naming
    def __str__(self):
        return self.title


class Region(TranslatableModel):
    # reference to country
    country = models.ForeignKey(
        to=Country,
        on_delete=models.CASCADE,
        related_name="region_country_ref",
    )
    titles = TranslatedFields(
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


class City(TranslatableModel):
    # reference to region
    region = models.ForeignKey(
        to=Region,
        null=True,
        on_delete=models.CASCADE,
    )

    titles = TranslatedFields(
        title=models.CharField(max_length=255)
    )
    # Meta
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

