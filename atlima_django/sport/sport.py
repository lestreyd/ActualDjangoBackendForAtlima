from django.db import models
from parler.models import TranslatedFields, TranslatableModel

# models for sport administrator


class SportAdministrator(models.Model):
    country = models.ForeignKey(
        'atlima_django.Country',
        related_name='sport_admin_country',
        on_delete=models.CASCADE,
        verbose_name="country",
    )
    region = models.ForeignKey(
        'atlima_django.Region',
        on_delete=models.CASCADE,
        verbose_name="region",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        'atlima_django.User',
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name="user",
    )
    # член СКС
    is_sks_member = models.BooleanField(
        default=False
    )
    # председатель СКС
    is_sks_president = models.BooleanField(
        default=False
    )
    # член коллегии судей
    is_referee_collegium_member = (
        models.BooleanField(default=False)
    )
    # председатель коллегии судей
    is_referee_collegium_president = (
        models.BooleanField(default=False)
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.user.last_name} {self.user.first_name} - {self.sport.id}"
            or ""
        )


class Sport(models.Model):
    """Sport model for sport representation"""

    titles = TranslatedFields(
                        title=models.CharField(max_length=255, blank=True, null=True),
                        description=models.TextField()
    )
    image = models.ImageField(upload_to="sports")
    slug = models.SlugField(
        max_length=255, unique=True
    )
    site = models.CharField(
        max_length=1024, null=True, blank=True
    )
    moderated = models.BooleanField(
        default=False,
    )
    administrators = models.ManyToManyField(SportAdministrator)
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"sport {str(self.id)}"
