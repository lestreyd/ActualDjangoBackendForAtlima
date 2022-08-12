from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class EventOffer(TranslatableModel):
    """Offer model for :model:Event"""

    FOR_USER = "For User"
    FOR_ORGANIZER = "For Organizer"

    offer_destination = (
        (FOR_USER, "For User"),
        (FOR_ORGANIZER, "For Organizer"),
    )

    content = TranslatedFields(
        text=models.CharField("text", max_length=32000),
    )

    destination = models.CharField(
        choices=offer_destination,
        max_length=15,
        default=FOR_USER,
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        strid = str(self.id)
        return f"offer_{strid}"
