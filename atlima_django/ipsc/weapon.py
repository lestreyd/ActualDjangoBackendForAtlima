from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class Weapon(TranslatableModel):
    """Weapon model for divisions"""
    titles = TranslatedFields(
        title = models.CharField(max_length=255)
    )
    image = models.ImageField(upload_to="weapons")
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = str(self.pk)
        return f"Weapon id{sid}"
