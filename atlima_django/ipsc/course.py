from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class Course(models.Model):
    """Course model for :model:Event"""

    # номер упражнения для сквозной нумерации упражнений
    course_number = (
        models.PositiveSmallIntegerField()
    )
    title = models.CharField(_('Tutle'), max_length=55)
    description = TranslatedFields(description = models.CharField(_('Description'), max_length=55))
    image = models.ImageField(upload_to="courses")

    # количество зачётных выстрелов
    scoring_shoots = (
        models.PositiveSmallIntegerField(
            null=True, blank=True
        )
    )
    # минимальное количество выстрелов
    minimum_shoots = (
        models.PositiveSmallIntegerField(
            null=True, blank=True
        )
    )
    # иллюстрация
    illustration = models.ImageField(
        upload_to="courses"
    )
    # зачётных выстрелов по картонным мишеням (при наличии картонных мишеней)
    scoring_paper = (
        models.PositiveSmallIntegerField(
            null=True, blank=True
        )
    )

    def __str__(self):
        return f"{self.title} (event id={self.event.id})"
