from django.db import models
from ..users.models import User
from atlima_django.event.promo_code import PromoCode
from atlima_django.money.currency import Currency
from atlima_django.ipsc.squad import Squad
from atlima_django.ipsc.discipline_ipsc import Discipline
from atlima_django.ipsc.team import Team


class Slot(models.Model):
    """User slot model for participating
    in the event. Contains all needed information
    about rating and results"""

    user = models.ForeignKey(
        to=User,
        db_index=True,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_for_slot"
    )

    promocode = models.ForeignKey(
        to=PromoCode,
        db_index=True,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="promocode_user_for_slot",
    )

    final_price = models.PositiveBigIntegerField()
    currency = models.ForeignKey(
        to=Currency,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="currency_for_slot",
    )

    participant_group = models.CharField(
        max_length=32,
        null=True,
        blank=True
    )
    participant_number = (
        models.PositiveSmallIntegerField(
            null=True, blank=True
        )
    )

    squad = models.ForeignKey(
        to=Squad,
        on_delete=models.SET_NULL,
        related_name="slot_squad_ref",
        blank=True,
        null=True,
    )

    # выбранная при регистрации дисциплина
    discipline = models.ForeignKey(
        to=Discipline,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # выбранная при регистрации категория участия
    SUPER_JUNIOR = 1
    JUNIOR = 2
    SENIOR = 3
    SUPER_SENIOR = 4
    LADY = 5
    REGULAR = 6

    categories = (
        (SUPER_JUNIOR, "Super Junior"),
        (JUNIOR, "Junior"),
        (SENIOR, "Senior"),
        (SUPER_SENIOR, "Super Senior"),
        (LADY, "Lady"),
        (REGULAR, "Regular"),
    )
    category = models.IntegerField(
        choices=categories, default=REGULAR
    )

    # выбранный при регистрации на событие фактор мощности
    MINOR = 1
    MAJOR = 2
    power_factors = (
        (MINOR, "Minor"),
        (MAJOR, "Major"),
    )
    power_factor = models.IntegerField(
        choices=power_factors, default=MINOR
    )
    team = models.ForeignKey(
        to=Team,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    active = models.BooleanField(
        default=False, verbose_name="Active"
    )
    paid = models.BooleanField(default=False)

    dont_include_in_rating_calculation = (
        models.BooleanField(default=False)
    )

    # общий расчёт для события
    percentage = models.FloatField(default=0)
    stage_points = models.FloatField(default=0)

    # поля для учёта рейтинга участника соревнований
    initial_rating = models.IntegerField(
        default=0, null=True, blank=True
    )
    deviation = models.FloatField(
        default=0, null=True, blank=True
    )
    handicap = models.FloatField(
        default=0, null=True, blank=True
    )
    performance = models.FloatField(
        default=0, null=True, blank=True
    )
    rating_increase = models.FloatField(
        default=0, null=True, blank=True
    )
    points = models.FloatField(
        default=0, null=True, blank=True
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        id = self.id
        if self.user:
            user_credentials = f"{self.user.first_name}_{self.user.last_name}"
        else:
            user_credentials = ""
        event_id = self.event.id
        participant_group = self.participant_group
        participant_number = (
            self.participant_number
        )
        return f"slot_{id}_{user_credentials}_G{participant_group}_№{participant_number}_{event_id}"
