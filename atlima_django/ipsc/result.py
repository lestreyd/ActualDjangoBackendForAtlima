from django.db import models
from .course import Course
from atlima_django.sport.slot import Slot
from .disqualification_reason import (
    DisqualificationReason,
)
from .discipline_ipsc import Discipline
from atlima_django.referee.referee_slot import RefereeSlot
from atlima_django.users.models import User


class SlotResult(models.Model):
    """Courses information about slot results"""

    slot = models.ForeignKey(
        to=Slot, on_delete=models.CASCADE
    )
    course = models.ForeignKey(
        to=Course, on_delete=models.CASCADE
    )
    course_points = models.FloatField(default=0)
    stage_points = models.FloatField(default=0)
    hit_factor = models.FloatField(default=0)

    def __str__(self):
        sid = str(self.id)
        return f"Slot id{sid}"


class AggregatedCourseResultForSlot(models.Model):
    """Результат упражнения содержит аггрегированное значение A,C,D,M,NS,P,T
    для упражнения по участнику"""

    client_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="Result UUID",
    )
    # тип результата
    GUNCHECK = 1
    COURSE_TARGET_RESULT = 2
    DISQUALIFICATION = 3

    result_types = (
        (GUNCHECK, "Guncheck"),
        (COURSE_TARGET_RESULT, "Course result"),
        (
            DISQUALIFICATION,
            "Disqualification (DNS/DQ)",
        ),
    )
    result_type = models.IntegerField(
        choices=result_types,
        default=COURSE_TARGET_RESULT,
    )

    # связь с участником
    slot = models.ForeignKey(
        to=Slot, on_delete=models.CASCADE
    )
    # связь с упражнением (если это Guncheck, может быть пустым)
    course = models.ForeignKey(
        to=Course,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # агрегированные результаты
    A = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    C = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    D = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    M = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    NS = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    # время
    T = models.FloatField(null=True, blank=True)

    # отметки для Guncheck
    discipline = models.ForeignKey(
        to=Discipline,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    category = models.IntegerField(
        choices=Slot.categories,
        null=True,
        blank=True,
    )
    power_factor = models.IntegerField(
        choices=Slot.power_factors,
        null=True,
        blank=True,
    )
    strong_hand = models.IntegerField(
        choices=User.hands, null=True, blank=True
    )

    # отметки о дисквалификации
    DNS = 1
    DQ = 2

    cancel_reasons = (
        (DNS, "Did not started"),
        (DQ, "Disqualified"),
    )
    cancellation = models.IntegerField(
        choices=cancel_reasons,
        default=None,
        null=True,
        blank=True,
    )
    cancel_reason = models.ForeignKey(
        to=DisqualificationReason,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    # фото
    photo = models.ImageField(
        upload_to="result_selfies",
        null=True,
        blank=True,
    )

    # судья
    # referee = models.ForeignKey(to=User, null=True, blank=True, on_delete=models.CASCADE)
    referee_slot = models.ForeignKey(
        to=RefereeSlot,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    # временные отметки
    timestamp = models.DateTimeField(
        null=True, blank=True
    )
    delete_timestamp = models.DateTimeField(
        null=True, blank=True
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    # возможность аннулировать результат
    active = models.BooleanField(default=True)

    def __str__(self):
        id = str(self.id)
        return f"result_{id}"
