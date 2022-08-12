from django.db import models


class Currency(models.Model):
    """
    Currencies from https://classifikators.ru/okv
    """

    digital_code = models.CharField(max_length=3)
    code = models.CharField(max_length=3)
    title = models.CharField(max_length=128)
    weight_in_list = (
        models.PositiveBigIntegerField(
            null=True, blank=True, default=0
        )
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code or self.title
