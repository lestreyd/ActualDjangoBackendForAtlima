from rest_framework import serializers
from atlima_django.common.models import Complain
from atlima_django.location.api.serializers import CitySerializer
from atlima_django.common.models import Organizer


# сериализатор жалоб на контент
class ComplainSerializer(serializers.ModelSerializer):
    # сериализатор Жалоб
    id = serializers.IntegerField(read_only=True)    
    class Meta:
        model = Complain
        exclude = ['created', 'updated']


   
class OrganizerSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField('get_title')
    city = serializers.SerializerMethodField('get_city')

    logo = serializers.SerializerMethodField('get_logo')

    def get_logo(self, obj):
        if obj.logo is not None:
            return obj.logo.photo.url
        else:
            return "-"

    class Meta:
        model = Organizer
        exclude = ['country', 'region']

    def get_city(self, obj):
        if obj.city is None: 
            return None
        else:
            serializer = CitySerializer
            serialized = serializer(obj.city)
            return serialized.data
        
        
class OrganizerMenuSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    logo = serializers.SerializerMethodField('get_photo_url')
    city = serializers.SerializerMethodField('get_city')

    def get_photo_url(self, obj):
        if obj.photo:
            return obj.photo.url

    def get_city(self, obj):
        if obj.city is None: return None
        serializer = CitySerializer
        serialized = serializer(obj.city)
        return serialized.data

    class Meta:
        model = Organizer
        exclude = ['country', 'region', 'slug', 'site', 'location', 'phone', 'email']