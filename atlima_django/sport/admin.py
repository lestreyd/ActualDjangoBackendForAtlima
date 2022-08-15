from parler.admin import TranslatableAdmin
from .models import Sport
from django.contrib import admin
from django.utils.html import format_html


    
# расширенная форма редактирования вида спорта
class ExtendedSportAdmin(TranslatableAdmin):
    model = Sport
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width=80 height=60 />'.format(obj.image.url))
        else:
            pass

    image_tag.short_description = 'Image'
    
    fieldsets = (
        ("Настройки вида спорта", {
            'fields': ('title', 'description', 'slug', 'image', 'site', 'moderated',)
        }),
    )
    list_display = ('title', 'image_tag', 'description', 'id', 'slug', 'site', 'created', 'updated')

admin.site.register(Sport, ExtendedSportAdmin)