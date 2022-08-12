from django.db import models
from .weapon import Weapon
from parler.models import TranslatableModel, TranslatedFields


class Division(TranslatableModel):
    """модель дивизиона для дисциплин"""

    descriptions = TranslatedFields(
        title=models.CharField(max_length=512),
        description=models.CharField(max_length=512)
    )

    weapon = models.ForeignKey(
        to=Weapon, on_delete=models.CASCADE
    )
    image = models.ImageField(
        upload_to="divisions",
        null=True,
        blank=True,
    )

    can_be_minor = models.BooleanField(
        default=True
    )
    can_be_major = models.BooleanField(
        default=True
    )

    custom_style = models.BooleanField(
        default=False
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
