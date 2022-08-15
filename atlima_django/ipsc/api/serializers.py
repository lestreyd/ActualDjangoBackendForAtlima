from ...sport_events.models import EventProperty
from atlima_django.ipsc.models import Weapon, Division, Discipline
from parler_rest.serializers import TranslatableModelSerializer
from parler_rest.fields import TranslatedFieldsField
from rest_framework import serializers
from atlima_django.ipsc.models import Course, AggregatedCourseResultForSlot
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.ipsc.models import CoursePenalty
from atlima_django.ipsc.api.serializers import CourseSerializer, CoursePenaltySerializer 


# базовый сериализатор для оружия
class WeaponSerializer(TranslatableModelSerializer):
    id = serializers.IntegerField(read_only=True)
    titles = TranslatedFieldsField(shared_model=Weapon)


# базовый сериализатор дивизиона
class DivisionSerializer(serializers.ModelSerializer):
    
    weapon = WeaponSerializer()

    class Meta:
        model = Division
        exclude = ['created', 'updated']


# базоаый сериализатор дисциплины
class DisciplineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discipline
        exclude = ['created', 'updated', 'active']
        
        
# базовый сериализатор для отдельного массива свойств
# практической стрельбы
class PSPropertySerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    disciplines = DisciplineSerializer(many=True)

    class Meta:
        model = EventProperty
        fields = '__all__'


# новый сериализатор, который возвращает только id
# дисциплин, которые вщиты в свойство события
class PSPropertySerializer2(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    disciplines = serializers.SerializerMethodField('get_disciplines')

    def get_disciplines(self, obj):
        disciplines = obj.disciplines.all()
        a = []
        for d in disciplines:
            a.append(d.id)
        return a

    class Meta:
        model = EventProperty
        fields = '__all__'
        

# сериализатор оружия для отображения в мероприятии        
class PropertyWeaponSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    title = serializers.SerializerMethodField('get_title')
    description = serializers.SerializerMethodField('get_description')
    logo = serializers.SerializerMethodField('get_logo')

    def get_logo(self, obj):
        if obj.logo:
            return obj.logo.logo.url
        return "-"

    class Meta:
        model = Weapon
        exclude = ['created', 'updated']
        
        
class DisqualificationViewSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    referee = serializers.SerializerMethodField('get_referee')

    def get_referee(self, obj):
        if obj.referee_slot is not None:
            return obj.referee_slot.id
        else:
            return "-"
    # course = serializers.SerializerMethodField('get_course')

    def get_course(self, obj):
        try:
            if obj.course is not None:
                course = Course.objects.get(id=obj.course.id)
            else:
                return ""
            serializer = CourseSerializer
            serialized = serializer(course, context={'request': self.context['request']})
            return serialized.data
        except ObjectDoesNotExist:
            return ""
    class Meta:
        model = AggregatedCourseResultForSlot
        exclude = ['result_type', 'A', 'C', 'D', 'M', 'NS', 'T', 'updated', 'category', 'power_factor', 'strong_hand', 'photo', 'course', 'discipline', 'referee_slot']
        
        
class TargetResultViewSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    # course = serializers.SerializerMethodField('get_course')
    course = serializers.IntegerField(source='course.id')
    penalties = serializers.SerializerMethodField('get_penalties')
    referee = serializers.SerializerMethodField('get_referee')

    def get_referee(self, obj):
        if obj.referee_slot is not None:
            return obj.referee_slot.id
        else:
            return "-"

    def get_course(self, obj):
        try:
            course = Course.objects.get(id=obj.course.id)
        except ObjectDoesNotExist:
            course = None
            return course
        serializer = CourseSerializer
        serialized = serializer(course, context={'request': self.context['request']})
        return serialized.data

    def get_penalties(self, obj):
        penalties = CoursePenalty.objects.filter(aggregated_result=obj, active=True).all()
        serializer = CoursePenaltySerializer
        serialized = serializer(penalties, context={'request': self.context['request']}, many=True)
        return serialized.data

    class Meta:
        model = AggregatedCourseResultForSlot
        exclude = ['result_type', 'cancellation', 'updated', 'cancel_reason', 'category', 'power_factor', 'strong_hand','referee_slot']
