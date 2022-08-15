from .models import Notification, NotificationTemplate
from django.contrib import admin

# расширенная форма редактирования уведомления
class ExtendedNotificationAdmin(admin.ModelAdmin):
    model = Notification

    fieldsets = (
        ("Настройки уведомления", {
            'fields': ('is_readed', 'atlima_obj_type', 'atlima_obj_id', 'target_user', 'system_event', 'notification_template')
        }),
    )

    list_display = ('id', 'system_event', 'notification_template', 'is_readed', 'atlima_obj_type',
                    'atlima_obj_id', 'target_user', 'created', 'updated')

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()

    def get_form(self, request, obj=None, *args, **kwargs):
        form = super(ExtendedNotificationAdmin, self).get_form(
            request, *args, **kwargs)

        user = request.user
        # form.base_fields['is_readed'].initial = False
        form.base_fields['atlima_obj_id'].initial = 0
        form.base_fields['target_user'].initial = user

        return form


# настройка шаблонов уведомления
class NotificationTemplateInline(admin.StackedInline):
    model = NotificationTemplate
    
    fields = ('content',)
    extra = 0
    min_num = 1
    max_num = 1
    can_delete=False
    can_delete_extra = False
    