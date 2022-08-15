from xmlrpc.client import Boolean
from django.contrib.auth.models import AbstractUser
from django.db.models import (CharField, 
                              DateField, 
                              ImageField, 
                              SlugField,
                              IntegerField,
                              ForeignKey,
                              BooleanField)
from django.urls import reverse
from atlima_django.location.models import Country, Region, City
from django.utils.translation import gettext_lazy as _

# from atlima_django.qualification.models import OfficialQualification
from django.db import models


class User(AbstractUser):
    """
    Default custom user model for atlima_django.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """
    name = CharField(max_length=255, db_index=True)
    first_name = CharField(max_length=255, 
                            null=True, 
                            blank=True)
    last_name = CharField(max_length=255,
                          blank=True,
                          null=True)
    patronym = CharField(max_length=255,
                         blank=True,
                         null=True)
    native_patronym = CharField(
        max_length=255,
        blank=True,
        null=True
    )
    native_firstname = CharField(max_length=255,
                                 null=True,
                                 blank=True)
    native_lastname = CharField(max_length=255,
                                blank=True,
                                null=True)
    birth_date = DateField(null=True, blank=True)
    phone = CharField(max_length=20, null=True, blank=True)
    
    image = ImageField(null=True, blank=True)
    
    M, F = "M", "F"
    sexes = [
        (M, "M"),
        (F, "F")]
    sex = CharField(choices=sexes, 
                    default=M, 
                    max_length=1)
    photo = ImageField(blank=True, null=True)
    slug = SlugField(null=True, blank=True, unique=True)
    vk_profile = CharField(max_length=255,
                           blank=True,
                           null=True)
    fb_profile = CharField(max_length=255,
                           blank=True,
                           null=True)
    instagram_profile = CharField(max_length=255,
                                  blank=True,
                                  null=True)
    
    LEFT_HAND = 1
    RIGHT_HAND = 2
    
    country = ForeignKey(
        to=Country, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index = True)
    
    region = ForeignKey(
        to=Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index = True
    )
    
    city = ForeignKey(
        to=City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )

    
    hands = (
        (RIGHT_HAND, 'Right'),
        (LEFT_HAND, 'Left')
    )

    strong_hand = IntegerField(choices=hands, default=RIGHT_HAND) 
    email_is_confirmed = BooleanField(
        default = False
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})


# class SportAdministrator(models.Model):
#     country = models.ForeignKey(
#         'atlima_django.Country',
#         related_name='sport_admin_country',
#         on_delete=models.CASCADE,
#         verbose_name="country",
#     )
#     region = models.ForeignKey(
#         'atlima_django.Region',
#         on_delete=models.CASCADE,
#         verbose_name="region",
#         null=True,
#         blank=True,
#     )
#     user = models.ForeignKey(
#         'atlima_django.User',
#         on_delete=models.CASCADE,
#         db_index=True,
#         verbose_name="user",
#     )
#     # член СКС
#     is_sks_member = models.BooleanField(
#         default=False
#     )
#     # председатель СКС
#     is_sks_president = models.BooleanField(
#         default=False
#     )
#     # член коллегии судей
#     is_referee_collegium_member = (
#         models.BooleanField(default=False)
#     )
#     # председатель коллегии судей
#     is_referee_collegium_president = (
#         models.BooleanField(default=False)
#     )
#     created = models.DateTimeField(
#         auto_now_add=True
#     )
#     updated = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return (
#             f"{self.user.last_name} {self.user.first_name} - {self.sport.id}"
#             or ""
#         )
