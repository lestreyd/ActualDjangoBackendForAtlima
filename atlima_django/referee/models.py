from django.db import models
from atlima_django.users.models import User
from django.db.models import Q
from rest_framework.views import APIView
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
# from atlima_django.sport_events.models import Event


# приглашение судьи на событие
# модератор должен подтвердить приглашение
# после чего для судьи будет создан судейский слот
# с отметкой его роли.
class EventRefereeInvite(models.Model):
    # модель приглашения судьи на мероприятие
    # пользователь, заявляющийся как судья
    user = models.ForeignKey(to=User, db_index=True, on_delete=models.CASCADE, related_name='event_judges_user')
    MAIN_REFEREE = 1                            # Главный судья
    MAIN_REFEREE_DEPUTY = 2                     # Заместитель ГС
    MAIN_SECRETARY = 3                          # Главный секретарь
    REFEREE = 4                                 # Судья
    SENIOR_EXERCISE_REFEREE = 5                 # старший судья упражнения
    SENIOR_REFEREE_OF_THE_EXERCISE_GROUP = 6    # старший судья группы упражнений
    WEAPONRY_REFEREE = 7                        # судья по вооружению
    TECH_REFEREE = 8                            # технический судья

    roles = (
        (MAIN_REFEREE, 'Main Referee'),
        (MAIN_REFEREE_DEPUTY, 'Main Referee Deputy'),
        (MAIN_SECRETARY, 'Main Secretary'),
        (REFEREE, 'Referee'),
        (SENIOR_EXERCISE_REFEREE, 'Senior Exercise Referee'),
        (SENIOR_REFEREE_OF_THE_EXERCISE_GROUP, 'Senior Referee of the Exercise Group'),
        (WEAPONRY_REFEREE, 'Weaponry Referee'),
        (TECH_REFEREE, 'Technical Referee')
    )

    # роль судьи на мероприятии
    role = models.IntegerField(choices=roles, default=MAIN_REFEREE)

    WAITING = 1
    APPROVED = 2
    DISMISSED = 3
    MODERATED = 4

    statuses = (
        (WAITING, 'Waiting'),
        (APPROVED, 'Approved'),
        (DISMISSED, 'Dismissed'),
        (MODERATED, 'Moderated')
    )

    # статус заявки
    status = models.IntegerField(choices=statuses, default=WAITING)

    # причина отказа
    dismiss_reason = models.TextField(null=True, blank=True)

    # временные отметки
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(to=User, on_delete=models.CASCADE, related_name='creator')

    def __str__(self):
        return f"{self.user}_{self.event.id}_{self.role}_{self.status}"


class RefereeSlot(models.Model):
    user = models.ForeignKey(
        to=User,
        related_name="user_referee_slot",
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
        blank=True
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
    
    role = models.IntegerField(
        choices=roles,
        default=REFEREE,
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)


# модель для оценки работы судей
class RefereeGrade(models.Model):
    """Модель оценки судейства"""

    referee_slot = models.ForeignKey(
        to=RefereeSlot, on_delete=models.CASCADE
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
