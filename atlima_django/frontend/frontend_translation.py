from django.db import models


class Translation(models.Model):
    """
    Language Package Model for serving translations from Frontend
    Fields:
    - lang_code - "ru" or "en"
    - data      - content in JSON format
    - created   - package creation time
    - updated   - package updating time
    """

    lang_code = models.CharField(
        max_length=5,
        null=False,
        blank=False,
        unique=True,
    )
    data = models.JSONField(
        null=False, blank=False
    )
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now=True)

    def __str__(self):
        return self.lang_code
