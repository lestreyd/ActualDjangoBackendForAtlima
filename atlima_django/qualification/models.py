from django.db import models
from atlima_django.sport.models import Sport
from uuid import uuid4
import os


# модель официальной квалификации пользователя
# после её получения пользователь может судить
# спортивные события на платформе 
class OfficialQualification(models.Model):
    """модель официальной квалификации пользователя"""

    # вид спорта
    sport_type = models.ForeignKey(
        to=Sport,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="qualification_sport",
    )

    # квалификация
    SPORT = 1
    REFEREE = 2
    INSTRUCTOR = 3

    qualifications = (
        (SPORT, "Sport qualification"),
        (REFEREE, "Referee qualification"),
        (INSTRUCTOR, "Instructor qualification"),
    )

    qualification = models.IntegerField(
        choices=qualifications, default=REFEREE
    )

    # категория

    JUNIOR_REFEREE = 1  # Юный судья
    SPORT_REFEREE_3 = (
        2  # Спортивный судья третьей категории
    )
    SPORT_REFEREE_2 = (
        3  # Спортивный судья второй категории
    )
    SPORT_REFEREE_1 = (
        4  # Спортивный судья первой категории
    )
    SPORT_REFEREE_AR = 5  # Спортивный судья всероссийской категории

    categories = (
        (JUNIOR_REFEREE, "Junior referee"),
        (SPORT_REFEREE_3, "Sport referee III"),
        (SPORT_REFEREE_2, "Sport referee II"),
        (SPORT_REFEREE_1, "Sport referee I"),
        (
            SPORT_REFEREE_AR,
            "Sport referee of the all-Russian",
        ),
    )

    category = models.IntegerField(
        choices=categories, default=JUNIOR_REFEREE
    )

    # файл
    document_file = models.FileField(
        null=True,
        blank=True,
        verbose_name="related_document_file",
    )

    # международный судья
    IROA = models.BooleanField(default=False)

    # одобрено/не одобрено
    approved = models.BooleanField(default=False)
    dismissed = models.BooleanField(default=False)
    dismiss_reason = models.CharField(
        max_length=4096, null=True, blank=True
    )
    approved_date = models.DateField(
        null=True, blank=True
    )

    # временные отметки
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def path_and_rename(instance, filename):
        upload_to = "official-qualifications"
        ext = filename.split(".")[-1]
        # get filename
        uuid = uuid4().hex
        if instance.pk:
            user_id = str(instance.user.id)
            sport = str(instance.sport_type.id)
            qual = str(instance.qualification)
            cat = str(instance.category)
            filename = f"oqdoc-u{user_id}-s{sport}-q{qual}-c{cat}-{uuid}.{ext}"
        else:
            filename = f"oqdoc-{uuid}.{ext}"
        # return the whole path to the file
        return os.path.join(upload_to, filename)
