from django.db import models
from .discipline_ipsc import Discipline
from .result import AggregatedCourseResultForSlot
from parler.models import TranslatableModel, TranslatedFields


class Penalty(models.Model):
    """Модель причин дисквалификации"""

    clause = models.CharField(max_length=16)
    disciplines = models.ManyToManyField(
        to=Discipline
    )
    cost_in_seconds = (
        models.PositiveSmallIntegerField(
            default=10
        )
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.clause


class CoursePenalty(models.Model):
    """ссылка на штраф в справочнике и количество штрафов"""

    aggregated_result = models.ForeignKey(
        to=AggregatedCourseResultForSlot,
        on_delete=models.CASCADE,
    )
    penalty = models.ForeignKey(
        to=Penalty, on_delete=models.CASCADE
    )
    amount = models.PositiveSmallIntegerField()
    active = models.BooleanField(default=True)
    created = models.DateTimeField(
        auto_now_add=True, null=True, blank=True
    )
    updated = models.DateTimeField(
        auto_now=True, null=True, blank=True
    )

    def __str__(self):
        return self.penalty.clause
