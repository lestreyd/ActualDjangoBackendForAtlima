from django.db import models


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
