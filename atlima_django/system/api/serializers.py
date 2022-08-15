from rest_framework import serializers
from atlima_django.system.models import SystemEventType, SystemObject


class SystemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemEventType
        exclude = ['created', 'updated']


class SystemObjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = SystemObject
        fields = '__all__'
