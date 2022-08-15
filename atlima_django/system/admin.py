from django.contrib import admin
from atlima_django.system.models import SystemEventType
from atlima_django.system.models import SystemEvent

# администрирование типов системных событий
class SystemEventTypeAdmin(admin.ModelAdmin):
    model = SystemEventType
    list_display = ['id', 'title', 'description', 'created', 'updated']

admin.site.register(SystemEventType, SystemEventTypeAdmin)


# администрирование системных событий
class SystemEventAdmin(admin.ModelAdmin):
    model = SystemEvent
    list_display = ['id', 'user', 'created', 'system_type', 'json_attributes']
    list_filter = ['user', 'system_type']
    search_fields = ['system_type__title', 'json_attributes', 'user__username']

admin.site.register(SystemEvent, SystemEventAdmin)
