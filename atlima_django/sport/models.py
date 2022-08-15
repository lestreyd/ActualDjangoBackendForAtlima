from django.db import models
from atlima_django.users.models import User
from parler.models import TranslatableModel, TranslatedFields
from atlima_django.location.models import Country, Region


# представление вида спорта с новыми текстовыми полями 
# администраторы включены в ролевую модель
class Sport(TranslatableModel):
    """Sport model for sport representation"""

    text = TranslatedFields(
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
    administrators = models.ManyToManyField(User)
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"sport {str(self.id)}"


# массив пользователей, администрирующих 
# конкретный вид спорта
class SportAdministrator(models.Model):

    sport = models.ForeignKey(to=Sport, 
                            on_delete=models.CASCADE, 
                            db_index=True,
                            verbose_name="sport")
    country = models.ForeignKey(to=Country,
                                on_delete=models.CASCADE, 
                                verbose_name="country")
    region = models.ForeignKey(to=Region,
                               on_delete=models.CASCADE, 
                               verbose_name="region", 
                               null=True, 
                               blank=True)
    user = models.ForeignKey(
        to=User, 
        on_delete=models.CASCADE, 
        db_index=True,
        verbose_name="user")
    # член СКС
    is_sks_member = models.BooleanField(default=False)
    # председатель СКС
    is_sks_president = models.BooleanField(default=False)
    # член коллегии судей
    is_referee_collegium_member = models.BooleanField(default=False)
    # председатель коллегии судей
    is_referee_collegium_president = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name} - {self.sport.id}" or ''