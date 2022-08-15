from rest_framework import serializers
from atlima_django.qualification.models import OfficialQualification
from ..models import RefereeSlot, RefereeGrade
from atlima_django.qualification.api.serializers import OfficialQualificationSerializer


# сериализатор оценок, проставленных за судейство
class RGSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefereeGrade
        exclude = ['event']
        

# базовый сериализатор судейского слота для события
class RefereeSlotSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    role = serializers.IntegerField()
    qualification = serializers.SerializerMethodField('get_qualification')
    user_id = serializers.IntegerField(source='user.id')

    def get_qualification(self, obj):
        user = obj.user
        qualification = OfficialQualification.objects.filter(user=user, qualification=OfficialQualification.REFEREE).last()
        if qualification is not None:
            serializer = OfficialQualificationSerializer
            serialized = serializer(qualification)
            return serialized.data
        else:
            return None

    class Meta:
        model = RefereeSlot
        exclude = ['event', 'created', 'updated', 'user']