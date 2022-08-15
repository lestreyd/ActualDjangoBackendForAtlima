from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.common.models import PrivacySetting
from  atlima_django.common.models import Complain

from atlima_django.location.models import Country, Region, City
from atlima_django.location.api.serializers import CitySerializer
from atlima_django.notifications.models import Notification
from rest_framework.authtoken.models import Token
from atlima_django.common.models import Organizer
from atlima_django.sport_events.models import Event

import json

User = get_user_model()

# сериализатор пользователя Атлима
class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(max_length=256, required=False)
    last_name = serializers.CharField(max_length=256, required=False)
    username = serializers.CharField(max_length=256, required=True)
    email = serializers.SerializerMethodField('get_email')
    phone = serializers.SerializerMethodField('get_phone')
    birth_date = serializers.SerializerMethodField('get_birth_date')
    strong_hand = serializers.SerializerMethodField('get_strong_hand')
    avatar = serializers.SerializerMethodField('get_profile_avatar')
    country_code = serializers.SerializerMethodField('get_country_code')
    is_staff = serializers.SerializerMethodField('get_is_staff')
    is_superuser = serializers.SerializerMethodField('get_is_superuser')
    
    def get_is_staff(self, obj):
        return obj.is_staff

    def get_is_superuser(self, obj):
        return obj.is_superuser

    def get_country_code(self, obj):
        if obj.country:
            country = obj.country
            alpha2 = country.alpha2
        else:
            alpha2 = None
        return alpha2

    def get_profile_avatar(self, obj):
        if obj.photo:
            return obj.photo.url
        return None

    def get_privacy_settings(self, user):
        try:
            privacy_settings = PrivacySetting.objects.get(user=user)
        except ObjectDoesNotExist:
            privacy_settings = None
        return privacy_settings

    def get_phone(self, obj):
        if obj.phone:
            return obj.phone
        return None

    def get_email(self, obj):
        if obj.email:
            return obj.email
        return None
        
    def get_birth_date(self, obj):
        if obj.birth_date:
            return obj.birth_date
        return None

    def get_strong_hand(self, obj):
        return obj.strong_hand


# сериализатор профиля (пользователя)
class ProfileSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField('get_user_info')
        
    profile_photo = serializers.SerializerMethodField(method_name='get_photo_url')
    phone = serializers.CharField(max_length=64, required=True)
    patronym = serializers.CharField(max_length=128, required=False)

    city = serializers.SerializerMethodField('get_city')
    region = serializers.SerializerMethodField('get_region')
    country = serializers.SerializerMethodField('get_country')

    sex = serializers.ChoiceField(choices=User.sexes)
    birth_date = serializers.DateField()

    native_firstname = serializers.CharField()
    native_lastname = serializers.CharField()
    native_patronym = serializers.CharField()

    alias = serializers.CharField(max_length=256, required=False)
    vk_profile = serializers.CharField(max_length=256, required=False)
    fb_profile = serializers.CharField(max_length=256, required=False)
    instagram_profile = serializers.CharField(max_length=256, required=False)
    email_is_confirmed = serializers.BooleanField()
    strong_hand = serializers.IntegerField()

    is_event_admin = serializers.SerializerMethodField('get_event_admin_status')
    is_organizer_admin = serializers.SerializerMethodField('get_organizer_admin_status')
    token = serializers.SerializerMethodField('get_token')
    has_unread_notif = serializers.SerializerMethodField('get_unread_notif')
    
    def get_user_info(self, obj):
        serializer = UserSerializer
        return serializer(obj).data

    def get_country(self, obj):
        country = Country.objects.filter(
            id = obj.country.id
        ).first()
        if country:
            return {
                "id": country.id,
                "title": country.title
            }
        return None
    
    def get_region(self, obj):
        region = Region.objects.filter(
            id = obj.region.id
        ).first()
        if region:
            return {
                "id": region.id,
                "title": region.title
            }
        return None
            
    def get_city(self, obj):
        city = City.objects.filter(
            id = obj.city.id
        ).first()
        if city:
            return {
                "id": city.id,
                "title": city.title
            }
        return None
        
    def get_unread_notif(self, obj):
        notifications = Notification.objects.filter(
            target_user=obj, 
            is_readed=False
            ).all()
        if notifications.count() > 0:
            return True
        return False


    def get_event_admin_status(self, obj):
        
        event_admin = Event.objects.filter(
            administrators__id=obj.id
        ).first()
        if event_admin is not None:
            return True
        return False
    

    def get_organizer_admin_status(self, obj):
        iamadmin = Organizer.objects.filter (
            administrators__id=obj.id
        ).first()
        if iamadmin is not None:
            return True
        return False
        
    def get_token(self, obj):
        token, created = Token.objects.get_or_create(user=obj)
        return token.key

    def get_photo_url(self, obj):
        if obj.photo:
            url = obj.photo.url
        else:
            url = None
        return url
    
    
# сериализатор настроек конфиденциальности
class PrivacySerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    blocked = serializers.SerializerMethodField('get_blocked')

    def get_blocked(self, obj):
        serializer = UserSerializer
        serialized = serializer(obj.blocked, many=True)
        return serialized.data

    class Meta:
        model = PrivacySetting
        fields = '__all__'
