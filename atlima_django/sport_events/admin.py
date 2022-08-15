from .models import Slot
from django.contrib import admin
from .models import Event
from django.utils.html import format_html
from parler.admin import TranslatableAdmin
from .models import EventFormat

# встроенная форма слота
# слот является основной единицей на платформе
# по слотам рассчитываются результаты, считаются рейтинги
# и так далее. Слот покупается за денежные средства
class SlotInline(admin.TabularInline):
    model = Slot
    fields = ('user', 'promocode', 'final_price', 'currency', 'active', 'participant_number', 'participant_group')
    extra=0
    can_delete=True
    

# расширенная форма редактирования события. Событие заполняется в приложении
# на четырёх экранах, учитывая дефолтные настройки в Constance для расчёта
# рейтинга и подсчёта результатов
class ExtendedEventAdmin(TranslatableAdmin):
    model = Event

    fieldsets = (
        ("Настройки события", {
            'fields': ('titles', 'sport_type', 'photo', 'site', 'status', 'location', 'country', 'region', 'city', 'slug', 'start_event_date', 'end_event_date', 'phone', 'email', 'completed', 'has_results',
                       'format', 'evsk', 'organizer', 'created_by', 'approved', 'imported', 'moderated',
                       'first_calculation_datetime', 'last_calculation_datetime')
        }),
        ("Регистрация", {
            'fields': ('registration_opened', 'price_option', 'price', 'currency',)
        }),
    )
    
    readonly_fields = ('created_by',)

    def image_tag(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width=160 height=120 />'.format(obj.photo.event_photo.url))
        else:
            pass

    image_tag.short_description = 'Image'
    
    list_display = ('id', 'image_tag', 'event_title', 'slug',
                    'sport_type', 'status',  
                    'city', 'start_event_date', 'end_event_date',
                    'organizer', 'price', 'currency',)

    search_fields = ('slug', 'site')
    list_filter = ['organizer', 'sport_type']
    
    
# формат события. От соревнований до клубных матчей
class EventFormatInline(TranslatableAdmin):
    model = EventFormat
    fields = ('title')

# расширенное администрирование заявок на судейство
class EventRefereeInviteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'event', 'role', 'status', 'dismiss_reason')
    search_fields = ('id', 'user__username', 'user__last_name', 'user__first_name', 'role', 'status')
    

