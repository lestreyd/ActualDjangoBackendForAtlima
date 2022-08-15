import json
from .models import FrontendLog, FrontendTranslation
from django.contrib import admin
from atlima_django.users.models import User
from django.utils.safestring import mark_safe
from django.db import models

# Модель администратора для логирования с фронтенда
# поле жэшируется и затем группируется с одинаковыми
# инцидентами с увеличением счётчика и рефрешем даты
# обновления
class FrontendLogAdmin(admin.ModelAdmin):

    readonly_fields = ['id', 'updated']
    list_display = ['id', 'date', 'counts', 'device_id', 
                    'build', 'get_user_name', 'message', 
                    'get_stack_trace', 'error_code', 
                    'log_date', 'updated',]
    list_filter = ('device_id', 'user')

    def get_stack_trace(self, obj):
        prep = mark_safe(f"<pre>{obj.stack_trace}</pre>")
        return prep

    def get_user_name(self, obj):
        user = obj.user
        if type(user) == User:
            return f"{obj.user.first_name} {obj.user.last_name}"
        else:
            return ""

    class Meta:
        model = FrontendLog
        fields = '__all__'

admin.site.register(FrontendLog, FrontendLogAdmin)
admin.site.register(FrontendTranslation)


