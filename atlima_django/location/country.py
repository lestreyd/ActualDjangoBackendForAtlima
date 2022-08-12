from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatedFields, TranslatableModel


class Country(TranslatableModel):
    # Names
    titles = TranslatedFields(title = models.CharField(_('Title'), max_length=255))

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
        return self.short_name
