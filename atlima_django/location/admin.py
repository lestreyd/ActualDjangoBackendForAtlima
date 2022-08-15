from urllib import request
from django.contrib import admin
from parler.admin import TranslatableAdmin
from .models import Country, Region, City


class CountryAdmin(TranslatableAdmin):
    list_display = ['id', 'title', 'alpha2', 'location', 'iso']

admin.site.register (Country, CountryAdmin)

class RegionAdmin(TranslatableAdmin):
    list_display = ['id', 'title', 'country', 'code']
    
admin.site.register (Region, RegionAdmin)

class CityAdmin (TranslatableAdmin):
    list_display = ['id', 'title', 'region']
    
admin.site.register (City, CityAdmin)