from django.db import models
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)


class PromoCode(models.Model):
    """promo codes for :model:Event,
    applied for :model:Slot"""

    # заголовок, от 5 до 8 знаков
    title = models.CharField(max_length=8)

    # размер скидки (от 0 до 100)
    discount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )

    # количество использований (от 1 до 1000)
    limit = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(1000),
        ]
    )

    # дата окончания действия промокода
    finish_date = models.DateField(
        null=True, blank=True
    )

    # активен ли промокод
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title
