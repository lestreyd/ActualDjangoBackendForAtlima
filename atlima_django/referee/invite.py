from django.db import models
from atlima_django.users.models import User


class EventRefereeInvite(models.Model):
    """Invite model for :model:User and :model:RefereeSlot
    approving of this invite triggering creation
    of new referee slot."""

    user = models.ForeignKey(
        to=User,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="event_judges_user",
    )

    MAIN_REFEREE = 1  # Главный судья
    MAIN_REFEREE_DEPUTY = 2  # Заместитель ГС
    MAIN_SECRETARY = 3  # Главный секретарь
    REFEREE = 4  # Судья
    SENIOR_EXERCISE_REFEREE = (
        5  # старший судья упражнения
    )
    SENIOR_REFEREE_OF_THE_EXERCISE_GROUP = (
        6  # старший судья группы упражнений
    )
    WEAPONRY_REFEREE = 7  # судья по вооружению
    TECH_REFEREE = 8  # технический судья

    roles = (
        (MAIN_REFEREE, "Main Referee"),
        (
            MAIN_REFEREE_DEPUTY,
            "Main Referee Deputy",
        ),
        (MAIN_SECRETARY, "Main Secretary"),
        (REFEREE, "Referee"),
        (
            SENIOR_EXERCISE_REFEREE,
            "Senior Exercise Referee",
        ),
        (
            SENIOR_REFEREE_OF_THE_EXERCISE_GROUP,
            "Senior Referee of the Exercise Group",
        ),
        (WEAPONRY_REFEREE, "Weaponry Referee"),
        (TECH_REFEREE, "Technical Referee"),
    )

    # роль судьи на мероприятии
    role = models.IntegerField(
        choices=roles, default=MAIN_REFEREE
    )

    WAITING = 1
    APPROVED = 2
    DISMISSED = 3
    MODERATED = 4

    statuses = (
        (WAITING, "Waiting"),
        (APPROVED, "Approved"),
        (DISMISSED, "Dismissed"),
        (MODERATED, "Moderated"),
    )

    # request status
    status = models.IntegerField(
        choices=statuses, default=WAITING
    )

    # reason of dismissing request
    dismiss_reason = models.TextField(
        null=True, blank=True
    )

    # meta
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    # user who create invite
    created_by = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name="creator",
    )

    def __str__(self):
        return f"{self.user}_{self.event.id}_{self.role}_{self.status}"
