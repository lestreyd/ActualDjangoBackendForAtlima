from django.db import models
from .division import Division
from parler.models import TranslatableModel, TranslatedFields


class Discipline(TranslatableModel):
    """Disciplines for IPSC"""
    names = TranslatedFields(
        name=models.CharField(
            max_length=255
        ),
        abbreviation=models.CharField(max_length=255)
    )

    division = models.ForeignKey(
        to=Division,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # типы соревнований
    INDIVIDUAL = 1
    TEAM = 2
    DUEL = 3

    competition_type_list = (
        (INDIVIDUAL, "Individual Competitions"),
        (TEAM, "Team competitions (4 ppl)"),
        (DUEL, "Duel"),
    )

    competition_type = models.IntegerField(
        choices=competition_type_list,
        default=1,
        blank=True,
        null=True,
    )

    # код дисциплины
    code = models.CharField(
        max_length=16, null=True, blank=True
    )
    # активна / неактивна
    active = models.BooleanField(default=True)
    standart_speed_courses = models.BooleanField(
        default=False
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = self.pk
        return f"discipline id{sid}"
