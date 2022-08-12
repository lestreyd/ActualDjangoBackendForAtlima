from django.db import models
from .discipline_ipsc import Discipline


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
