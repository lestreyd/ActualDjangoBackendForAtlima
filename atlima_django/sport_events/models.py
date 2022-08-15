from django.db import models
from atlima_django.location.models import Country
from atlima_django.location.models import Region
from atlima_django.location.models import City
from atlima_django.sport.models import Sport
from atlima_django.users.models import User
from atlima_django.money.models import (
    PriceConfiguration,
)
from atlima_django.common.models import Organizer
from atlima_django.money.models import Currency
from atlima_django.notifications.models import Notification
from atlima_django.system.models import SystemObject
from atlima_django.referee.models import RefereeSlot
from atlima_django.ipsc.models import AggregatedCourseResultForSlot, Course
from atlima_django.ipsc.models import Team
from parler.models import TranslatedFields, TranslatableModel
from atlima_django.ipsc.models import Squad, Discipline
from atlima_django.money.models import PromoCode
from django.contrib import admin


class Slot(models.Model):
    """User slot model for participating
    in the event. Contains all needed information
    about rating and results"""

    user = models.ForeignKey(
        to=User,
        db_index=True,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_for_slot"
    )

    promocode = models.ForeignKey(
        to=PromoCode,
        db_index=True,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="promocode_user_for_slot",
    )

    final_price = models.PositiveBigIntegerField()
    currency = models.ForeignKey(
        to=Currency,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="currency_for_slot",
    )

    participant_group = models.CharField(
        max_length=32,
        null=True,
        blank=True
    )
    participant_number = (
        models.PositiveSmallIntegerField(
            null=True, blank=True
        )
    )

    squad = models.ForeignKey(
        to=Squad,
        on_delete=models.SET_NULL,
        related_name="slot_squad_ref",
        blank=True,
        null=True,
    )

    # выбранная при регистрации дисциплина
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
        choices=categories, default=REGULAR
    )

    # выбранный при регистрации на событие фактор мощности
    MINOR = 1
    MAJOR = 2
    power_factors = (
        (MINOR, "Minor"),
        (MAJOR, "Major"),
    )
    power_factor = models.IntegerField(
        choices=power_factors, default=MINOR
    )
    team = models.ForeignKey(
        to=Team,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    active = models.BooleanField(
        default=False, verbose_name="Active"
    )
    paid = models.BooleanField(default=False)

    dont_include_in_rating_calculation = (
        models.BooleanField(default=False)
    )
    
    raw_results = models.ManyToManyField(AggregatedCourseResultForSlot)
    
    # общий расчёт для события
    percentage = models.FloatField(default=0)
    stage_points = models.FloatField(default=0)

    # поля для учёта рейтинга участника соревнований
    initial_rating = models.IntegerField(
        default=0, null=True, blank=True
    )
    deviation = models.FloatField(
        default=0, null=True, blank=True
    )
    handicap = models.FloatField(
        default=0, null=True, blank=True
    )
    performance = models.FloatField(
        default=0, null=True, blank=True
    )
    rating_increase = models.FloatField(
        default=0, null=True, blank=True
    )
    points = models.FloatField(
        default=0, null=True, blank=True
    )
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{str(self.id)}"


class EventFormat(TranslatableModel):
    """Event format for representing in event common
    interface"""

    text = TranslatedFields(title=models.CharField(max_length=255))
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        sid = self.pk
        return f"event format id{sid}"


class EventProperty(models.Model):
    """
    specific Event attributes for :model:Event
    """

    sport = models.ForeignKey(
        Sport, on_delete=models.CASCADE
    )
    disciplines = models.ManyToManyField(
        to=Discipline
    )
    match_level = models.SmallIntegerField(
        default=0, null=True, blank=True
    )
    squads_amount = models.PositiveIntegerField(
        default=0, null=True, blank=True
    )
    shooters_in_squad = (
        models.PositiveIntegerField(
            default=0, null=True, blank=True
        )
    )
    prematch = models.BooleanField(default=False)
    standart_speed_courses = models.BooleanField(
        default=False
    )
    number_in_calendar_plan = models.CharField(
        max_length=64, null=True, blank=True
    )

    def __str__(self):
        strid = str(self.id)
        return f"property_{strid}"


class EventEVSKStatus(TranslatableModel):
    """evsk model for :model:Event"""

    name = TranslatedFields(title=models.CharField(max_length=256))

    REGIONAL = 1
    FEDERAL = 2
    regional_statuses = [
        (REGIONAL, "Regional"),
        (FEDERAL, "Federal"),
    ]
    regional_status = models.IntegerField(
        choices=regional_statuses,
        default=1,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class Event(TranslatableModel):
    """
    Event model for event representation in Atlima.
    Can be object with status Draft or Publish.
    Users can register to the event and participate
    in sport events with result checking and rating
    calculation.
    """

    photo = models.ImageField(upload_to="events")
    properties = models.OneToOneField(
        EventProperty,
        on_delete=models.CASCADE
    )

    titles = TranslatedFields(
        title=models.CharField(max_length=255),
        description=models.CharField(max_length=255)
    )

    slots = models.ManyToManyField(Slot)
    referee_slots = models.ManyToManyField(
        RefereeSlot
    )
    courses = models.ManyToManyField(Course)

    address = models.CharField(
        max_length=4096, null=True, blank=True
    )
    start_event_date = models.DateField(
        null=True, blank=True
    )
    end_event_date = models.DateField(
        null=True, blank=True
    )

    country = models.ForeignKey(
        to=Country,
        on_delete=models.CASCADE,
        related_name="event_country",
        null=True,
        blank=True,
    )
    region = models.ForeignKey(
        to=Region,
        on_delete=models.CASCADE,
        related_name="event_region",
        null=True,
        blank=True,
    )

    city = models.ForeignKey(
        to=City,
        on_delete=models.CASCADE,
        related_name="event_city",
        null=True,
        blank=True,
    )
    sport_type = models.ForeignKey(
        to=Sport,
        related_name="event_sport_type",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    site = models.CharField(
        max_length=512, null=True, blank=True
    )

    DRAFT = "Draft"
    PUBLISH = "Publish"
    DELETED = "Deleted"

    statuses = [
        (DRAFT, "DRAFT"),
        (PUBLISH, "PUBLISH"),
        (DELETED, "DELETED"),
    ]

    status = models.CharField(
        choices=statuses,
        max_length=32,
        default=DRAFT,
        null=True,
        blank=True,
    )

    format = models.ForeignKey(
        to=EventFormat,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="event_format",
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    approved = models.BooleanField(default=False)

    organizer = models.ForeignKey(
        to=Organizer,
        related_name="event_organizer",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    registration_opened = models.BooleanField(
        default=False
    )
    price_option = models.ForeignKey(
        to=PriceConfiguration,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="event_price_option",
    )
    price = models.DecimalField(
        max_digits=17,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
    )
    currency = models.ForeignKey(
        to=Currency,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="currency_registration_price",
    )

    evsk = models.ForeignKey(
        to=EventEVSKStatus,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    standart_speed_courses = models.BooleanField(
        default=False
    )
    created_by = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="event_created_by",
    )

    phone = models.CharField(
        max_length=512, null=True, blank=True
    )
    email = models.EmailField(
        null=True, blank=True
    )

    completed = models.BooleanField(default=False)
    has_results = models.BooleanField(
        default=False
    )
    imported = models.BooleanField(default=False)
    dismissed = models.BooleanField(default=False)
    dismiss_reason = models.CharField(
        max_length=4096, null=True, blank=True
    )
    moderated = models.BooleanField(default=False)

    banned = models.BooleanField(
        default=None, null=True, blank=True
    )
    banned_moderation = models.BooleanField(
        default=False
    )

    freezed = models.BooleanField(default=False)

    first_calculation_datetime = (
        models.DateTimeField(
            null=True, blank=True
        )
    )
    last_calculation_datetime = (
        models.DateTimeField(
            null=True, blank=True
        )
    )

    director = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='director'
    )

    interested = models.ManyToManyField(User, related_name='interested_in', null=True, blank=True)
    administrators = models.ManyToManyField(User, related_name='administrators')
    promocodes = models.ManyToManyField(PromoCode)
    teams = models.ManyToManyField(Team)

    def __str__(self):
        return self.slug or str(self.created)

    def delete(self, *args, **kwargs):
        notifications = Notification.objects.filter(
            object_type=SystemObject.objects.get(
                title="event", object_id=self.id
            )
        ).all()
        notifications.delete()

        super(Event, self).delete()
        
        
        
# ЕВСК регулирует, будет ли матч проходить
# модерацию. ЕВСК статус может быть региональным,
# федеральным или неофициальным.
class ExtendedEVSKAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'regional_status']
    class Meta:
        model = EventEVSKStatus
        fields = '__all__'
        
admin.site.register(EventEVSKStatus, ExtendedEVSKAdmin)


class EventAdministration(models.Model):
    """администрирование события для пользователей"""
    
    event = models.ForeignKey(to=Event, related_name='related_event_for_admin', on_delete=models.CASCADE)
    user = models.ForeignKey(to=User, related_name='related_user_for_admin', on_delete=models.CASCADE)
    is_director = models.BooleanField(default=False, blank=True, null=True, verbose_name='Director')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.user.first_name} {self.user.user.last_name} - {self.event}"
    
    class Meta:
        unique_together = ['event', 'user']


class UserInterestedIn(models.Model):

    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    event = models.ForeignKey(to=Event, on_delete=models.CASCADE)

    def __str__(self):
        return f"user{self.user.id}-event{self.event.id}"
    

    class Meta:
        unique_together = ['user', 'event']