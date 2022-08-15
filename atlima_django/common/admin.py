from django.contrib import admin
from .models import (Complain, ConfirmationActivity, 
                     EmailTemplate, EventOffer, PrivacySetting,
                     Organizer)
from parler.admin import TranslatableAdmin
from django.utils.html import format_html


# админ-панель для просмотра и редактирования жалоб.
# позволяет просмотреть жалобы и совершить с ними действия
# любого характера
class ComplainAdmin(admin.ModelAdmin):
    # админка для жалоб
    list_display = ('id', 'object_type', 'object_id', 'user', 'user_ip', 'reason', 'status', 'moderator', 'created', 'updated')

    class Meta:
        model = Complain
        fields = '__all__'

admin.site.register(Complain, ComplainAdmin)        


# подтверждение электронной почты и телефона из панели
# администратора происходит здесь. Для юзера присваивается
# код, который он должен ввести.
class ConfirmationActivityAdmin(admin.ModelAdmin):
    readonly_fields = ['id']
    list_display = ['id', 'user', 'action', 'data', 'target', 'status']
    search_fields = ['target', 'data']

    class Meta:
        model = ConfirmationActivity
        fields = '__all__'
        
admin.site.register(ConfirmationActivity, ConfirmationActivityAdmin)


# Панель администратора для просмотра и редактирования
# шаблона электронного письма. Используется в качестве
# приветственных писем и оповещений
class EmailTemplateAdmin (TranslatableAdmin):
    list_display = ['translatable',  'created',  'updated']
    
admin.site.register(EmailTemplate, EmailTemplateAdmin)


# Панель администратора для просмотра и редактирования
# оффера для мероприятия или организатора. Позволяет управлять
# контентом из админки.
class EventOfferAdmin (TranslatableAdmin):
    list_discplay = ['content', 'destination',]
    
admin.site.register(EventOffer, EventOfferAdmin)


# Панель администратора для редактирования организатора
# позволяет вести заголовки на разных языках
class OrganizerAdmin(TranslatableAdmin):
    readonly_fields = ['id',]

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width=80 height=60 />'.format(obj.image.url))
        else:
            pass

    image_tag.short_description = 'Image'

    list_display = ('id', 'image_tag', 'title', 'description', 'slug', 'site', 'country', 'region', 'city', 'address', 'phone', 'email')

    fieldsets = (
        ("Настройки организатора", {
            'fields': ('id', 'title', 'description', 'image', 'slug', 'site', 'country', 'region', 'city', 'address', 'phone', 'email')
        }),
    )

admin.site.register(Organizer, OrganizerAdmin)

# админка для тонкой настройки конфиденциальности внутри
# системы. Позволяет скрыть телефон и почту, а также
# блокирует пользователей и сообщения.
class PrivacySettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user_first_name', 'get_user_last_name', 'phone_visibility', 
                    'email_visibility', 'want_to_get_mails_from_atlima',
                    'who_can_send_messages')
    
    def get_user_first_name(self, obj):
        return obj.user.first_name
    
    def get_user_last_name(self, obj):
        return obj.user.last_name

    class Meta:
        model = PrivacySetting
        fields = '__all__'

admin.site.register(PrivacySetting, PrivacySettingsAdmin)