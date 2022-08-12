from django.db import models
from atlima_django.users.models import User
from parler.models import TranslatedFields, TranslatableModel


class ConfirmationActivity(TranslatableModel):
    # phone and mail confirmation for user
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
        blank=True,
    )
    action = models.CharField(_('Action'), max_length=32)
    data = models.CharField(max_length=64)
    target = models.CharField(max_length=128)
    status = models.PositiveSmallIntegerField()
    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        id = str(self.id)
        return f"confirmation_id{id}"
