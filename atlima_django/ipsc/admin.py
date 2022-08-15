from django.contrib import admin
from .models import (Course, 
                     TargetSet, 
                     Penalty, 
                     CoursePenalty, 
                     AggregatedCourseResultForSlot,
                     SlotResult,
                     TargetType,
                     Target,
                     Weapon,
                     Squad)
from atlima_django.sport_events.models import EventFormat
from django.utils.html import format_html
from atlima_django.sport_events.models import Slot
from parler.admin import TranslatableAdmin
from .models import DisqualificationReason
from .models import Discipline, Division

# встроенная модель мишени для практической стрельбы
# каждая мишень имеет свою стоимость и различные применения
# в различных дисциплинах. Бумажные мишени считаются по А = 5,
# стальные и разбивающиеся тарелки могут быть также 10 и 15.
# Для модифицированных дисциплин используются моодифицированные 
# мишени
class TargetSetInline(admin.TabularInline):
    model = TargetSet
    max_num=20
    extra=1
    fields = ('id', 'target_type', 'course_target_array', 'amount', 'alpha_cost')

# каждое упражнение представляет из себя набор контента (изображение + описание с мультиязычностью.
# В курсе также есть тонкая настройка стоимости и количества мишеней за попадание в A.
# Позднее результаты упражнений используются для расчёта результатов.
class CourseExtendedAdmin(TranslatableAdmin):
    model = Course

    inlines = [TargetSetInline]
    list_display = ('id', 'course_number', 'title', 'event', 'scoring_shoots', 'scoring_paper', 'minimum_shoots', 'illustration')
    fieldsets = (
        ("Настройки курса", {
            'fields': ('course_number', 'title', 'event', 'scoring_shoots', 'scoring_paper', 'minimum_shoots', 'illustration')
        }),
    )
    
admin.site.register(Course, CourseExtendedAdmin)


# причина дисквалификации спортсмена с матча
class DisqualificationReasonAdmin(TranslatableAdmin):
    model = DisqualificationReason
    list_display = ['title', 'created', 'updated']

admin.site.register(DisqualificationReason, DisqualificationReasonAdmin)

# администрирование штрафов, здесь их можно удалить
# или добавить новый. Штрафы заранее определены в 
# системе, как и их стоимость
class PenaltyAdmin(admin.ModelAdmin):
    model = Penalty
    list_display = ('id', 'clause', 'cost_in_seconds')
    readonly_fields = ['id', ]
    fieldsets = (
        ("Penalty Control", {
            'fields': ('id', 'clause', 'cost_in_seconds', 'created', 'updated')
        }),
    )
    
admin.site.register(Penalty, PenaltyAdmin)


# встроенная форма штрафа за упражнение   
class CoursePenaltyInline(admin.TabularInline):
    model = CoursePenalty
    fields = ['penalty', 'amount']
    extra = 1
    min_num = 0
    max_num = 20
    
# форма администрирования для результатов, полученных ранее с фронта.
# позже система их должна пересчитать и составить на основе этих показателей
# результат спортсмена в соревновании
class AggregatedResultsAdmin(admin.ModelAdmin):
    model = AggregatedCourseResultForSlot
    readonly_fields = ['id', 'created', 'updated']

    list_display = ['id', 'result_type', 'course', 'referee_slot', 'active']

    fieldsets = (
        ("Общие", {
            'fields': ('id', 'result_type', 'course', 'photo', 'referee_slot', 'created', 'updated', 'active')
        }),
        ("Guncheck", {
            'fields': ('discipline', 'category', 'power_factor', 'strong_hand')
        }),
        ("Упражнение", {
            'fields': ('A', 'C', 'D', 'M', 'NS', 'T')
        }),
        ("Дисквалификация", {
            'fields': ('cancellation', 'cancel_reason')
        }),
    )

    inlines = [CoursePenaltyInline]

admin.site.register(AggregatedCourseResultForSlot, AggregatedResultsAdmin)


# встроенная форма резульата упражнения по слоту
# каждый раз рассчитывается по завершённому событию.
class SlotResultInline(admin.TabularInline):
    model = SlotResult
    fields = ('id', 'slot', 'course', 'course_points', 'stage_points', 'hit_factor')
    

# встроенный слот с информацией об участнике события
class SlotInline(admin.TabularInline):
    model = Slot
    fields = ('user', 'promocode', 'final_price', 'currency', 'active', 'participant_number', 'participant_group')
    extra=0
    can_delete=True


# панель для управления скводами в админке
class SquadAdmin(admin.ModelAdmin):

    list_display = ('id', 'squad_number', 'squad_date', 'comment', 'is_blocked')
    search_fields = ('id', 'squad_number')
    inlines = [SlotInline,]
    
admin.site.register(Squad, SquadAdmin)
    
# тип мишени в панели администратора
class TargetInline(admin.StackedInline):
    model = TargetType
    fields = ('titles', 'target_type')
    extra = 0
    min_num = 1
    max_num = 1
    can_delete=False
    can_delete_extra = False
    
    
# управление типами мишеней и добавление новых
# vмишень может быть бумажной или металлической,
# разбивающейся, модифицированной и так далее
class ExtendedTargetAdmin(admin.ModelAdmin):
    model = Target

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:15px;height:25px;"/>'.format(obj.image.url))
        else:
            pass

    image_tag.short_description = 'Image'

    list_display = ('id', 'image_tag', 'paper', 'allowed_result')
    fieldsets = (
        ("Настройки шаблона", {
            'fields': ('image', 'paper', 'allowed_result')
        }),
    )
    
admin.site.register(Target, ExtendedTargetAdmin)   


# встроенная форма набора мишеней, который необходимо отстрелять в
# упражнении. Каждая такая форма собирается перед началом события
# с автоматическим расчётом очков и рейтингов по ним.
class TargetSetInline(admin.TabularInline):
    model = TargetSet
    max_num=20
    extra=1
    fields = ('id', 'target_type', 'course_target_array', 'amount', 'alpha_cost')



# встроенная форма редактирования вида оружия
# позволяет установить изображение, заголовок и
# описание для оружия
class WeaponAdmin(TranslatableAdmin):
    model = Weapon
    fields = ('titles', 'description',)

admin.site.register(Weapon, WeaponAdmin)
    
    
# формат соревнования во встроенной форме  
class EventFormatInline(admin.StackedInline):
    model = EventFormat
    fields = ( 'title', 'description',)
    extra = 0
    min_num = 1
    max_num = 1
    can_delete = False
    can_delete_extra = False
    create_from_default = True    

# дисциплина в практической стрельбе, содержит в
# себе как объект дивизион, в который вложено оружие
# все дисциплины соответствуют тем, которые преждоставлены
# Атлимой
class PSDiscipline(TranslatableAdmin):
    model = Discipline

    def image_tag(self, obj):
        if obj.division.image:
            return format_html('<img src="{}" style="width: 160px;height:80px;"/>'.format(obj.division.image.url))
        else:
            pass

    image_tag.short_description = 'Image'
    
    ordering = ('active', 'division', 'competition_type')
    readonly_fields = ['id',]
    search_fields = ['code', 'division', 'competition_type']

    list_display = ('id', 'image_tag', 'division', 'can_be_minor', 'can_be_major', 'discipline_name', 'code', 'competition_type', 'active')
    list_filter = ('division', 'competition_type', 'active')

    def can_be_minor(self, obj):
        return obj.division.can_be_minor
    
    def can_be_major(self, obj):
        return obj.division.can_be_major

    def discipline_name(self, obj):
        weapon = Weapon.objects.filter(weapon=obj.division.weapon).first()
        if obj.competition_type == 1:
            compet = ""
        elif obj.competition_type == 2:
            compet = "- team competitions (4 members)"
        else:
            compet = "- duel shooting"
        if obj.division.description_en is not None:
            return f"{obj.division.name} - {weapon}, {obj.division.description_en} {compet}"
        else:
            return f"{obj.division.name} - {weapon} {compet}"
   
admin.site.register(Discipline, PSDiscipline)     
        
# дивизион, привязан к конкретному виду
# оружия,    
class DivisionAdmin(TranslatableAdmin):
    model = Division
    
    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 160px;height:80px;"/>'.format(obj.image.url))
        else:
            pass

    image_tag.short_description = 'Image'
    
    list_display = ('id', 
                    'image_tag',
                    'descriptions',
                    'weapon', 
                    'can_be_minor', 
                    'can_be_major',
                    'descriptions')

    ordering = ('id',)

admin.site.register(Division, DivisionAdmin)


