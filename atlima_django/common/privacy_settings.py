from django.db import models
# from .user import User


class PrivacySetting(models.Model):
    # privacy configuration for specific user
    ALL = 1
    ONLY_SUBSCRIBERS = 2
    ONLY_ME = 3

    visibility_options = [
        (ALL, "All"),
        (ONLY_SUBSCRIBERS, "Only subscribers"),
        (ONLY_ME, "Only me"),
    ]

    phone_visibility = (
        models.PositiveSmallIntegerField(
            choices=visibility_options,
            default=ALL,
        )
    )

    email_visibility = (
        models.PositiveSmallIntegerField(
            choices=visibility_options,
            default=ALL,
        )
    )

    want_to_get_mails_from_atlima = (
        models.BooleanField(default=False)
    )
    who_can_send_messages = (
        models.PositiveSmallIntegerField(
            choices=visibility_options,
            default=ALL,
        )
    )

    blocked = models.ManyToManyField(
        to='core.User', related_name="blocked_users"
    )

    def __str__(self):
        id = str(self.id)
        return f"privacy_{id}_{self.user.last_name}_{self.user.first_name}"
