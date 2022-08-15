from django.db import models
from atlima_django.system.models import SystemObject
from atlima_django.users.models import User
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatedFields, TranslatableModel
from atlima_django.location.models import Country, City, Region


class Complain(models.Model):
    """Complain model for user complain service"""

    object_type = models.ForeignKey(
        to=SystemObject, on_delete=models.CASCADE
    )
    object_id = models.BigIntegerField()

    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    user_ip = models.CharField(
        max_length=120, blank=True, null=True
    )

    SPAM = 1
    FORBIDDEN_CONTENT = 2
    FRAUD = 3
    COPYRIGHT = 4
    VIOLENCE = 5
    PERSONAL_DATA = 6

    complain_reasons = (
        (SPAM, "SPAM"),
        (FORBIDDEN_CONTENT, "FORBIDDEN CONTENT"),
        (FRAUD, "FRAUD"),
        (COPYRIGHT, "COPYRIGHT"),
        (VIOLENCE, "VIOLENCE"),
        (PERSONAL_DATA, "PERSONAL DATA"),
    )

    reason = models.IntegerField(
        choices=complain_reasons, default=SPAM
    )

    APPROVED = 1
    DECLINED = 2

    complain_statuses = (
        (APPROVED, "APPROVED"),
        (DECLINED, "DECLINED"),
    )

    status = models.IntegerField(
        choices=complain_statuses,
        default=None,
        null=True,
        blank=True,
    )
    moderator = models.ForeignKey(
        to=User,
        related_name="complain_moderator",
        on_delete=models.SET_NULL,
        db_index=True,
        null=True,
        blank=True,
    )
    moderator_ip = models.CharField(
        max_length=120, blank=True, null=True
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        if type(self.user) == User:
            un = f"{self.user.last_name} {self.user.first_name}"
        else:
            un = "Guest"
        if type(self.moderator) == User:
            mn = f"{self.moderator.last_name} {self.moderator.first_name}"
        else:
            mn = "Guest"
        oid = str(self.object_id)
        return f"complain_{self.object_type}_id{oid}_{un}_mod_{mn}"


class ConfirmationActivity(TranslatableModel):
    # phone and mail confirmation for user
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
        blank=True,
    )
    action = models.CharField(_('Action'), max_length=32)
    data = models.CharField(max_length=64)
    target = models.CharField(max_length=128)
    status = models.PositiveSmallIntegerField()
    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        id = str(self.id)
        return f"confirmation_id{id}"


class EmailTemplate(TranslatableModel):
    """Template for Email"""

    translatable = TranslatedFields(
        template_name=models.CharField(
            max_length=256
        ),
        description=models.TextField(),
        text=models.TextField()
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = str(self.id)
        return f"email_template{sid}"


class EventOffer(TranslatableModel):
    """Offer model for :model:Event"""

    FOR_USER = "For User"
    FOR_ORGANIZER = "For Organizer"

    offer_destination = (
        (FOR_USER, "For User"),
        (FOR_ORGANIZER, "For Organizer"),
    )

    content = TranslatedFields(
        text=models.CharField("text", max_length=32000),
    )

    destination = models.CharField(
        choices=offer_destination,
        max_length=15,
        default=FOR_USER,
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        strid = str(self.id)
        return f"offer_{strid}"


class Organizer(TranslatableModel):
    """
    Organizer model for events. User
    with organizer role can create
    new event
    """

    image = models.ImageField(
        upload_to="organizers"
    )

    titles = TranslatedFields(
        title=models.CharField(max_length=255),
        description=models.CharField(max_length=255)
    )

    slug = models.SlugField(
        max_length=255, unique=True
    )
    site = models.URLField()
    country = models.ForeignKey(
        to=Country,
        related_name="organizer_country",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    region = models.ForeignKey(
        to=Region,
        related_name="organizer_region",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    city = models.ForeignKey(
        to=City,
        related_name="organizer_city",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    address = models.TextField()
    phone = models.CharField(
        max_length=256, null=True, blank=True
    )
    email = models.EmailField(
        null=True, blank=True
    )
    imported = models.BooleanField(default=False)
    administrators = models.ManyToManyField(User)

    def __str__(self):
        sid = str(self.pk)
        return f"organizer id{sid}"


class PrivacySetting(models.Model):
    # privacy configuration for specific user
    ALL = 1
    ONLY_SUBSCRIBERS = 2
    ONLY_ME = 3
    
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)

    visibility_options = [
        (ALL, "All"),
        (ONLY_SUBSCRIBERS, "Only subscribers"),
        (ONLY_ME, "Only me"),
    ]

    phone_visibility = (
        models.PositiveSmallIntegerField(
            choices=visibility_options,
            default=ALL,
        )
    )

    email_visibility = (
        models.PositiveSmallIntegerField(
            choices=visibility_options,
            default=ALL,
        )
    )

    want_to_get_mails_from_atlima = (
        models.BooleanField(default=False)
    )
    who_can_send_messages = (
        models.PositiveSmallIntegerField(
            choices=visibility_options,
            default=ALL,
        )
    )

    blocked = models.ManyToManyField(
        to=User, related_name="blocked_users"
    )
    

    def __str__(self):
        id = str(self.id)
        return f"privacy_{id}_{self.user.last_name}_{self.user.first_name}"


class OrganizerAdministration(models.Model):
    """
    модель для хранения записей об администрировании конкретной записи об 
    организаторе, используется связь профиль - ссылка на объект "организатор" 
    в справочнике организаторов.
    
    Позже используется в роуте event/can_update для проверки наличия разрешения 
    на обновление объекта
    """
    organizer_record = models.ForeignKey(to=Organizer, 
                                        on_delete=models.CASCADE, 
                                        related_name='related_organizer_admin_id', 
                                        verbose_name='Organizer')
    profile_record = models.ForeignKey(to=User, 
                                        on_delete=models.CASCADE, 
                                        related_name='related_profile_admin_id', 
                                        verbose_name='Profile')
    
    # временные отметки
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
      return self.organizer_record.slug
    
    class Meta:
        unique_together = ['organizer_record', 'profile_record']