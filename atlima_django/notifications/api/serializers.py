from rest_framework import serializers
from models import Notification
from atlima_django.users.api.serializers import UserSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from django.conf import settings
from atlima_django.users.models import User
from django.http import JsonResponse
from atlima_django.sport_events.models import Event
from atlima_django.common.models import Organizer
from atlima_django.system.models import SystemObject
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.ipsc.api.serializers import PracticalShootingPropertySerializer
from atlima_django.sport_events.api.serializers import EventModelSerializer, EventProperty
from atlima_django.notifications.models import NotificationTemplate
from atlima_django.sport.api.serializers import SportAdminSerializer
from atlima_django.common.models import OrganizerAdministration
from atlima_django.sport.models import SportAdministrator
from atlima_django.common.api.serializers import OrganizerAdminSerializer
from atlima_django.system.api.serializers import SystemObjectSerializer

# сериализатор всех полей для уведомления
class NotificationSerializer(serializers.ModelSerializer):
    """
        Базовый сериализатор для уведомлений
    """
    class Meta:
        model = Notification
        fields = '__all__'


# обёртка для уведомления
class NotificationWrapperSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    is_readed = serializers.BooleanField()
    atlima_obj_type = serializers.IntegerField(source='atlima_obj_type.id')
    atlima_obj_id = serializers.IntegerField()
    target_user = UserSerializer()
    
    
    
# ВЫДАЧА УВЕДОМЛЕНИЙ С КУРСОРНОЙ ПАГИНАЦИЕЙ
class CursorNotificationList(APIView):

    authentication_classes = [TokenAuthentication]

    def get(self, request):
        cursor = request.GET.get('cursor', "0")
        limit = request.GET.get('limit', settings.CURSOR_PAGINATION_LIMIT)

        serializer = NotificationPageSerializer
        user = self.request.user
        # limit = settings.CURSOR_PAGINATION_LIMIT

        cursor = int(cursor)
        limit = int(limit)

        if cursor is not None and cursor != 0:    

            if type(user) == User:
                notifications = Notification.objects.filter(target_user=user, id__lt=cursor).all().order_by('-created')[:limit]
                if notifications.count() > 0:
                    serialized = serializer(notifications, many=True, context={'request': request})
                    notifications = serialized.data
                else:
                    notifications = []
            else:
                notifications = []
        else:
            if type(user) == User:
                notifications = Notification.objects.filter(target_user=user).all().order_by("-created")
                notifications = notifications[:limit]
                serialized = serializer(notifications, many=True, context={'request': request})
                notifications = serialized.data
            else:
                notifications = []
        
        return JsonResponse(notifications, safe=False)



class NotificationPageSerializer(serializers.ModelSerializer):
    """
        Базовый сериализатор для уведомлений
    """
    content = serializers.SerializerMethodField('get_content')
    system_type = serializers.SerializerMethodField('get_system_type')
    object_type = serializers.SerializerMethodField('get_type')

    def get_type(self, obj):
        system_type = obj.atlima_obj_type
        serializer = SystemObjectSerializer
        serialized = serializer(system_type)
        return serialized.data

    def get_event_title(self, language, event):
        return event.title


    def get_organizer_title(self, language, organizer):
        return organizer.title


    def get_sport_title(self, language, sport_type):
        return sport_type.title


    def get_event_data(self, object_id, json_content):
        
        try:
            specific_object = Event.objects.get(id=object_id)
        except ObjectDoesNotExist:
            specific_object = None

        if specific_object:
            serializer = EventModelSerializer
            serialized = serializer(specific_object, context={'request': self.context['request']})
            result = serialized.data    
            city = specific_object.city
            result['event_city_ru'] = city.settlement
            result['event_city_en'] = city.english_name

            squad_number = json_content.get('squad_number')

            if squad_number: result['squad_number'] = squad_number
            
            property_object = EventProperty.objects.get(event=specific_object)
            property_serializer = PracticalShootingPropertySerializer
            property_serialized = property_serializer(property_object)
            property_serialized_data = property_serialized.data
            for k, v in property_serialized_data.items():
                result.update({k: v})
            return result
        else:
            return {}

    def get_user_data(self, object_id):
        specific_object = User.objects.get(id=object_id)
        serializer = UserSerializer
        serialized = serializer(specific_object)
        result = serialized.data
        return result


    def get_sport_permission_data(self, object_id):
        permission_obj = SportAdministrator.objects.get(id=object_id)
        serializer = SportAdminSerializer
        serialized = serializer(permission_obj)
        result = serialized.data
        return result

    
    def get_organizer_admin_data(self, object_id):
        permission_obj = OrganizerAdministration.objects.get(id=object_id)
        serializer = OrganizerAdminSerializer
        serialized = serializer(permission_obj)
        result = serialized.data


    def get_object_from_system_object(self, system_event_type, object_id, json_content):
        """
            получить словарь с объектом и его полями
        """
        result = None
        if system_event_type == "user_registered_on_event":
            result = self.get_event_data(object_id, json_content)
        elif system_event_type == "user_added":
            result = self.get_user_data(object_id)
        elif system_event_type == "user_sport_type_permission_added":
            result = self.get_sport_permission_data(self, object_id)
        elif system_event_type == "organizer_admin_added":
            result = self.get_organizer_admin_data(self, object_id)
        elif system_event_type == "event_admin_added":
            result = self.get_event_data(object_id, json_content)
        elif system_event_type == "event_participant_invite":
            result = self.get_event_data(object_id, json_content)
        elif system_event_type == "squad_number_changed":
            result = self.get_event_data(object_id, json_content)
        elif system_event_type == "slot_added_to_squad":
            result = self.get_event_data(object_id, json_content)

        return result

    def create_notification_content_from_template(self, notification):
        """
            Получить контент из шаблона, сделать подстановку, сформировать контент
            отправить пользователю.
        """
        # тип системного уведомлений
        system_event_type = notification.system_event.system_type.title
        # event
        system_object = notification.system_event.system_type.system_object
        # json attributes from system event
        json_content = notification.system_event.json_attributes
        # event id from json attributes
        system_object_id = json_content['id']
        # all event fields
        system_object_dict = self.get_object_from_system_object(system_event_type, system_object_id, json_content)

        # allowed_keys = system_object_dict.keys()
        notification_template = notification.notification_template
        templates = NotificationTemplate.objects.filter(id=notification_template.id).all()

        for notification_content in templates:
            template_content = notification_content.content
            variables_list = template_content.split(' ')
            default_variables = [template_variable for template_variable in variables_list if
                                 template_variable[0] == "$"]
            mapping = {}
            for template_variable in default_variables:
                json_attribute = template_variable[1:].replace(',', '').replace('.', '').replace('!', '').replace(';', '')
                template_variable_for_mapping = template_variable.replace(',', '').replace('.', '').replace('!', '').replace(';', '')
                try:
                    mapping[template_variable_for_mapping] = system_object_dict[json_attribute]
                except KeyError:
                    mapping[template_variable_for_mapping] = ''

            for k, v in mapping.items():
                if v:
                    template_content = template_content.replace(k, str(v))
                else:
                    template_content = template_content.replace(k, '')

            return template_content
    
    def get_content(self, obj):
        template = obj.notification_template
        if template is not None:
            notification_content = self.create_notification_content_from_template(obj)
        if template is None:
            notification_content = "No template"
        return notification_content

    def get_system_type(self, obj):
        return obj.system_event.system_type.title

    class Meta:
        model = Notification
        exclude = ['atlima_obj_type', 'system_event', 'notification_template', 'target_user']