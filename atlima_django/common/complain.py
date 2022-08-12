from django.db import models
from atlima_django.sport.system import SystemObject
from atlima_django.users.models import User
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatedFields, TranslatableModel


class Complain(models.Model):
    """Complain model for user complain service"""

    object_type = models.ForeignKey(
        to=SystemObject, on_delete=models.CASCADE
    )
    object_id = models.BigIntegerField()

    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    user_ip = models.CharField(
        max_length=120, blank=True, null=True
    )

    SPAM = 1
    FORBIDDEN_CONTENT = 2
    FRAUD = 3
    COPYRIGHT = 4
    VIOLENCE = 5
    PERSONAL_DATA = 6

    complain_reasons = (
        (SPAM, "SPAM"),
        (FORBIDDEN_CONTENT, "FORBIDDEN CONTENT"),
        (FRAUD, "FRAUD"),
        (COPYRIGHT, "COPYRIGHT"),
        (VIOLENCE, "VIOLENCE"),
        (PERSONAL_DATA, "PERSONAL DATA"),
    )

    reason = models.IntegerField(
        choices=complain_reasons, default=SPAM
    )

    APPROVED = 1
    DECLINED = 2

    complain_statuses = (
        (APPROVED, "APPROVED"),
        (DECLINED, "DECLINED"),
    )

    status = models.IntegerField(
        choices=complain_statuses,
        default=None,
        null=True,
        blank=True,
    )
    moderator = models.ForeignKey(
        to=User,
        related_name="complain_moderator",
        on_delete=models.SET_NULL,
        db_index=True,
        null=True,
        blank=True,
    )
    moderator_ip = models.CharField(
        max_length=120, blank=True, null=True
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        if type(self.user) == User:
            un = f"{self.user.last_name} {self.user.first_name}"
        else:
            un = "Guest"
        if type(self.moderator) == User:
            mn = f"{self.moderator.last_name} {self.moderator.first_name}"
        else:
            mn = "Guest"
        oid = str(self.object_id)
        return f"complain_{self.object_type}_id{oid}_{un}_mod_{mn}"
