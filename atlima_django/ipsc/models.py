
from django.db import models
from django.contrib import admin
from parler.models import TranslatableModel, TranslatedFields
from atlima_django.sport.models import Sport
from atlima_django.users.models import User
from atlima_django.referee.models import RefereeSlot

# модель упражнения, используется для представления упражнения
# в системе с очками и мишенями. Дополнительно можно добавить
# иллюстрацию.
class Course(TranslatableModel):
    """Course model for :model:Event"""

    # номер упражнения для сквозной нумерации упражнений
    course_number = models.PositiveSmallIntegerField()

    title = models.CharField(max_length=255)
    description = TranslatedFields(text = models.CharField(max_length=55))
    image = models.ImageField(upload_to="courses")

    # количество зачётных выстрелов
    scoring_shoots = models.PositiveSmallIntegerField(null=True, blank=True)

    # минимальное количество выстрелов
    minimum_shoots = models.PositiveSmallIntegerField(
            null=True, blank=True
        )
    # иллюстрация
    illustration = models.ImageField(
        upload_to="courses"
    )
    # зачётных выстрелов по картонным мишеням (при наличии картонных мишеней)
    scoring_paper =  models.PositiveSmallIntegerField(
            null=True, blank=True
        )

    def __str__(self):
        return f"{self.title} (event id={self.event.id})"

# причина дисквалификации
class DisqualificationReason(TranslatableModel):
    """Модель причин дисквалификации"""
    title = TranslatedFields(text=models.CharField(max_length=255))
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = str(self.id)
        return f"Disqualification {sid}"


# оружие
class Weapon(TranslatableModel):
    """Weapon model for divisions"""
    titles = TranslatedFields(
        title = models.CharField(max_length=255),
        description = models.CharField(max_length=255)
    )
    image = models.ImageField(upload_to="weapons")
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = str(self.pk)
        return f"Weapon id{sid}"


class Division(TranslatableModel):
    """модель дивизиона для дисциплин"""

    descriptions = TranslatedFields(
        title=models.CharField(max_length=512),
        description=models.CharField(max_length=512)
    )

    weapon = models.ForeignKey(
        to=Weapon, on_delete=models.CASCADE
    )
    image = models.ImageField(
        upload_to="divisions",
        null=True,
        blank=True,
    )

    can_be_minor = models.BooleanField(
        default=True
    )
    can_be_major = models.BooleanField(
        default=True
    )

    custom_style = models.BooleanField(
        default=False
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Discipline(TranslatableModel):
    """Disciplines for IPSC"""
    names = TranslatedFields(
        name=models.CharField(
            max_length=255
        ),
        abbreviation=models.CharField(max_length=255)
    )

    sport = models.ForeignKey(to=Sport, on_delete=models.CASCADE)

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


class Team(models.Model):
    """Team model for Team Competition"""

    title = models.CharField(max_length=512)
    discipline = models.ForeignKey(
        to=Discipline, on_delete=models.CASCADE
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Target(TranslatableModel):
    """Target model for :model:TargetSet"""

    NS = "NS"
    A = "A"
    AC = "AC"
    ACD = "ACD"

    allowed_results = (
        (NS, "NS"),
        (A, "A"),
        (AC, "AC"),
        (ACD, "ACD"),
    )

    allowed_result = models.CharField(
        max_length=10,
        choices=allowed_results,
        default=ACD,
    )
    image = models.ImageField(
        upload_to="targets", null=True, blank=True
    )
    paper = models.BooleanField(default=False)

    def __str__(self):
        return f"Target id{str(self.id)}"


class TargetType(TranslatableModel):

    titles = TranslatedFields(
        title=models.CharField(max_length=255)
    )
    target_type = models.ForeignKey(
        to=Target, on_delete=models.CASCADE
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Squad(models.Model):
    # новая модель сквода для слота
    squad_number = models.PositiveIntegerField()
    comment = models.CharField(
        max_length=512, null=True, blank=True
    )
    squad_date = models.DateTimeField(
        null=True, blank=True
    )
    is_blocked = models.BooleanField(
        default=False
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.event.id} - id{self.id}:#{self.squad_number}"


class SlotResult(models.Model):
    """Courses information about slot results"""

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
        choices=categories,
        null=True,
        blank=True,
    )


    MINOR, MAJOR = 1, 2
    power_factors = [
        (MINOR, "MINOR"),
        (MAJOR, "MAJOR")
    ]

    power_factor = models.IntegerField(
        choices=power_factors,
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


class TargetSet(models.Model):
    """Набор мишеней"""

    target_type = models.ForeignKey(
        to=Target,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    course_target_array = models.ForeignKey(
        to=Course, on_delete=models.CASCADE
    )
    # количество мишеней данного типа
    amount = models.PositiveSmallIntegerField()
    # Стоимость Альфа: может быть 5, 10 и 15 в зависимости от сложности выстрела
    alpha_cost = models.PositiveSmallIntegerField(
        null=True, blank=True
    )

    def __str__(self):
        id = str(self.id)
        return f"target_type_{id}"
