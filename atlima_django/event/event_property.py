from django.db import models
from atlima_django.ipsc.discipline_ipsc import Discipline
from atlima_django.sport.sport import Sport


class EventProperty(models.Model):
    """
    specific Event attributes for :model:Event
    """

    sport = models.ForeignKey(
        Sport, on_delete=models.CASCADE
    )
    disciplines = models.ManyToManyField(
        to=Discipline
    )
    match_level = models.SmallIntegerField(
        default=0, null=True, blank=True
    )
    squads_amount = models.PositiveIntegerField(
        default=0, null=True, blank=True
    )
    shooters_in_squad = (
        models.PositiveIntegerField(
            default=0, null=True, blank=True
        )
    )
    prematch = models.BooleanField(default=False)
    standart_speed_courses = models.BooleanField(
        default=False
    )
    number_in_calendar_plan = models.CharField(
        max_length=64, null=True, blank=True
    )

    def __str__(self):
        strid = str(self.id)
        return f"property_{strid}"
