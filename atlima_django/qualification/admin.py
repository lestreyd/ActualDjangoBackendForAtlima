from django.contrib import admin
from .models import OfficialQualification

# управление официальной квалификацией в панели администратора
class OfficialQualificationAdmin(admin.ModelAdmin):
    model = OfficialQualification
    list_display = ('id', 'user', 'sport_type', 'qualification', 'category', 'IROA', 'approved')
    search_fields = ('id', 'user__username', 'user__first_name', 'user__last_name', 'qualification', 'category')