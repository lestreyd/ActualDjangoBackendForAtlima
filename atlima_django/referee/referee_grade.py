from django.db import models
from atlima_django.referee.referee_slot import RefereeSlot
from atlima_django.event.event import Event


class RefereeGrade(models.Model):
    """Модель оценки судейства"""

    referee_slot = models.ForeignKey(
        to=RefereeSlot, on_delete=models.CASCADE
    )
    event = models.ForeignKey(
        to=Event, on_delete=models.CASCADE
    )

    EXCELLENT = 5
    GOOD = 4
    SATISFACTORILY = 3
    UNSATISFACTORILY = 2

    grades = (
        (EXCELLENT, "Excellent"),
        (GOOD, "Good"),
        (SATISFACTORILY, "Satisfactorily"),
        (UNSATISFACTORILY, "Unsatisfactorily"),
    )

    grade = models.IntegerField(
        choices=grades, default=EXCELLENT
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        id = str(self.id)
        return f"referee_grade_{id}"
