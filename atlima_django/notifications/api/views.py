from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from ..models import NotificationTemplate
from atlima_django.sport_events.models import Event, Slot
from atlima_django.sport_events.api.serializers import EventModelSerializer
from atlima_django.sport_events.models import EventProperty
from atlima_django.sport_events.api.serializers import EventPropertySerializer
from atlima_django.notifications.models import Notification, NotificationTemplate
from atlima_django.notifications.api.serializers import NotificationSerializer
from django.http import JsonResponse
import json
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.users.models import User
from atlima_django.users.api.views import UserSerializer
from datetime import datetime
from atlima_django.referee.models import RefereeSlot
from atlima_django.common.api.utils import create_system_event_object
from django.db.models import Q
from atlima_django.sport_events.models import EventFormat
from atlima_django.ipsc.api.serializers import DisciplineSerializer
from atlima_django.sport_events.api.utils import get_event_participants
from django.conf import settings
from atlima_django.notifications.api.serializers import NotificationPageSerializer
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.views import generics


# Notifications endpoints
class GetNotifications(APIView):
    """
        Get all notifications for specific user (by token)
        You can specify amount of notifications for output
    """
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object_from_system_object(self, system_object, object_id, request):
        """
            получить словарь с объектом и его полями
        """
        result = None
        if system_object.title == "event":
            specific_object = Event.objects.get(id=object_id)

            serializer = EventModelSerializer
            serialized = serializer(specific_object, context={'request': request})
            result = serialized.data
            
            property_object = EventProperty.objects.get(event=specific_object)
            property_serializer = EventPropertySerializer
            property_serialized = property_serializer(property_object)

            property_serialized_data = property_serialized.data
            for k, v in property_serialized_data.items():
                result.update({k: v})
        else:
            return JsonResponse({"status": False, "message": "Cant create content for this event type"})

        return result
    
    def create_notification_content_from_template(self, notification, request):
        """
            Получить контент из шаблона, сделать подстановку, сформировать контент
            отправить пользователю.
        """
        # event
        system_object = notification.system_event.system_type.system_object
        # json attributes from system event
        json_content = notification.system_event.json_attributes
        # event id from json attributes
        system_object_id = json_content['id']
        # all event fields
        system_object_dict = self.get_object_from_system_object(
            system_object, 
            system_object_id, 
            request)

        allowed_keys = system_object_dict.keys()
        notification_template = notification.notification_template
        templates = NotificationTemplate.objects.filter(
            related_notification_template=notification_template
            ).all()

        for notification_content in templates:
            template_content = notification_content.content
            variables_list = template_content.split(' ')
            default_variables = [template_variable for template_variable in variables_list if
                                 template_variable[0] == "$"]
            mapping = {}
            for template_variable in default_variables:
                json_attribute = template_variable[1:]
                try:
                    mapping[template_variable] = system_object_dict[json_attribute]
                except KeyError:
                    mapping[template_variable] = ''

            for k, v in mapping.items():
                if v:
                    template_content = template_content.replace(k, v)
                else:
                    template_content = template_content.replace(k, '')
            return template_content

    def post(self, request):
        received_json_data = json.loads(request.body)
        amount = received_json_data.get('amount')
        amount = 100 if not amount else int(amount)
        notifications = Notification.objects.filter(target_user=request.user).order_by('-created')[:amount]

        content = []
        for notification in notifications:
            if notification.notification_template is not None:
                try:
                    notification_content = self.create_notification_content_from_template(notification, request)
                    serializer = NotificationSerializer
                    serialized = serializer(notification)
                    notification_object = serialized.data
                    notification_object['content'] = notification_content
                    content.append(notification_object)
                except:  # noqa
                    pass
            if notification.notification_template is None:
                serializer = NotificationSerializer
                serialized = serializer(notification)
                notification_object = serialized.data
                notification_object['content'] = ''
                content.append(notification_object)
        return JsonResponse(content, safe=False)
    

# установить уведомления как прочтённые   
class MarkAsReaded(APIView):
    """
        Set "is_readed" flag to True and "read_date" to now.
        You can specify ID for readed notification or mark all objects as readed.
    """
    authentication_classes = [TokenAuthentication,]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        data = request.data

        specific_id = data.get('id')

        if specific_id is not None:
            try:
                specific_notification = Notification.objects.filter(
                    id=specific_id).first()
            except ObjectDoesNotExist:
                specific_notification = None

            if specific_notification is not None:
                specific_notification.is_readed = True
                specific_notification.save()
                return JsonResponse({"status": True}, 
                                    safe=False, 
                                    status=200)

            return JsonResponse({"status": False, 
                                 "message": "Notification not found"}, 
                                safe=False, 
                                status=404)
        else:
            user = request.user
            queryset = Notification.objects.filter(
                target_user=user, 
                is_readed=False).order_by("-created")
            for notification_instance in queryset:
                notification_instance.is_readed = True
                notification_instance.save()
            return JsonResponse({"status": True}, safe=False, status=200)
        

# получить данные пользователя по ID        
class UserProfileById(APIView):
    """Возвращает пользователя по ID"""
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, id):
        serializer = UserSerializer
        try:
            user = User.objects.get(id=id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False,  
                                "errors": {"user": ['not found']}},
                                status=404)
        serialized = serializer(user)
        return JsonResponse(serialized.data, safe=False)
    
 
 # роут мягкого удаления пользователя
 # пользователь становится неактивным, 
 # а его учётная запись переименовывается в _deleted_timestamp   
class DeleteUser(APIView):
    """
        "Мягкое" удаление пользователя из системы:
        Пользователь становится неактивным.
        Имя пользователя меняется на username_deleted_<timestamp>
    """

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def is_sport_admin(user):
        return user.groups.filter(name__startswith='Администратор вида спорта').exists()
    
    def is_event_admin(user):
        return user.groups.filter(name__startswith='Администратор События').exists()
    
    def delete(self, request):
        old_user = request.user
        data = request.data
        now = datetime.now()

        try:
            password = data['password']
        except KeyError:
            return JsonResponse({"status": False, 
                                 "message": "Can't delete, password is required"}, 
                                status=400)

        current_slot = Slot.objects.filter(Q(user=old_user)&Q(event__start_event_date__gte=now)).all()
        if current_slot.count() > 0:
            return JsonResponse({"status": False, 
                                 "message": "Can't delete, cause you have active slot"}, 
                                status=400)
        
        current_referee = RefereeSlot.objects.filter(Q(user=old_user)&Q(event__start_event_date__gte=now)).all()
        if current_referee.count() > 0:
            return JsonResponse({"status": False, 
                                 "message": "Can't delete cause you have referee slot"}, 
                                status=400)
        
        if self.is_sport_admin(old_user):
            return JsonResponse({"status": False, 
                                 "message": "Can't delete, cause you are sport admin"}, 
                                status=400)
            
        if self.is_event_admin(old_user):
            return JsonResponse({"status": False, 
                                 "message": "Can't delete, cause you are event admin"}, 
                                status=400)

        if old_user.check_password(password):
            
            try:
                user = old_user
                user.is_active = False
                now = str(datetime.now())
                user.username = user.username + f'_deleted_{now}'
                user.save()
            except Exception:
                return JsonResponse({"status": False}, status=400)
            
            # создаём системное событие для удалённого пользователя
            try:
                create_system_event_object(old_user, 'user_deleted', {"id": user.id})
            except:
                pass
        else:
            return JsonResponse({"status": False, "message": "Password is wrong"}, status=400)

        return JsonResponse({"status": True}, safe=False, status=200)
 
    
class EventManagement(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, event_id):
        event = Event.objects.get(id=event_id)
        event_parameters = {}

        event_parameters['title'] = event.title
        event_parameters['description'] = event.description

        if event.sport_type:
            event_parameters['sport_type'] = event.sport.title

        if event.photo:
            event_parameters['photo'] = event.photo.event_photo.url

            # 4 Статус
            event_parameters['status'] = event.status
            
            # 5 Адресная информация
            language = self.get_language(request=request)
            if language.code == 'ru':
                if event.country:
                    event_parameters['country'] = {'id': event.country.id, 'title': event.country.short_name}
                else:
                    event_parameters['country'] = None
                if event.region:
                    event_parameters['region'] = {'id': event.region.id, 'title': event.region.title}
                else:
                    event_parameters['region'] = None
                if event.city:
                    event_parameters['city'] = {'id': event.city.id, 'title': event.city.settlement}
                else:
                    event_parameters['city'] = None
            else:
                if event.country:
                    event_parameters['country'] = {'id': event.country.id, 'title': event.country.english_name}
                else:
                    event_parameters['country'] = None
                if event.region:
                    event_parameters['region'] = {'id': event.region.id, 'title': event.region.english_name}
                else:
                    event_parameters['region'] = None
                if event.city:
                    event_parameters['city'] = {'id': event.city.id, 'title': event.city.english_name}
                else:
                    event_parameters['city'] = None

            event_parameters['location'] = event.location
            event_parameters['site'] = event.site

            # slug
            event_parameters['slug'] = event.slug

            # даты
            event_parameters['start_event_date'] = event.start_event_date
            event_parameters['end_event_date'] = event.end_event_date

            # формат
            try:
                format_content = EventFormat.objects.get(format=event.format, language=self.get_language(request=request))
            except ObjectDoesNotExist:
                format_content = None

            if format_content:
                event_parameters['format'] = format_content.title
            
            event_parameters['approved'] = event.approved

            # 3 проверяем на динамические свойства
            
            try:
                practical_shooting_properties = EventProperty.objects.get(event=event)
            except ObjectDoesNotExist:
                practical_shooting_properties = {}
                event_parameters['properties'] = {}


            if practical_shooting_properties:


                event_parameters['properties'] = {}

                if practical_shooting_properties.disciplines is not None:
                    serializer = DisciplineSerializer
                    serialized = serializer(practical_shooting_properties.disciplines, many=True)
                    data = serialized.data
                    event_parameters['properties']['disciplines'] = data
                else:
                    event_parameters['properties']['disciplines'] = []
                event_parameters['properties']['id'] = practical_shooting_properties.id
                event_parameters['properties']['match_level'] = practical_shooting_properties.match_level
                event_parameters['properties']['exercices_amount'] = practical_shooting_properties.exercices_amount
                event_parameters['properties']['min_shoots_amount'] = practical_shooting_properties.min_shoots_amount
                event_parameters['properties']['squads_amount'] = practical_shooting_properties.squads_amount
                event_parameters['properties']['shooters_in_squad'] = practical_shooting_properties.shooters_in_squad
                event_parameters['properties']['prematch'] = practical_shooting_properties.prematch
            event_parameters['participants'] = get_event_participants(event)
            return JsonResponse(event_parameters, safe=False, status=200)


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



# просмотр уведомлений в постраничном варианте
# максимальное количество уведомлений на странице - 100
class NotificationPaginator(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationList(generics.ListAPIView):
    
    authentication_classes = [BasicAuthentication, TokenAuthentication,]
    serializer_class = NotificationPageSerializer
    pagination_class = NotificationPaginator
    
    def get_queryset(self):
        user = self.request.user
        if type(user) == User:
            return Notification.objects.filter(target_user=user)
        else:
            return []


class NotificationListv2(generics.ListAPIView):
    
    serializer_class = NotificationPageSerializer
    pagination_class = LimitOffsetPagination
    
    def get_queryset(self):
        if self.request.version == '1.0':
            user = self.request.user
            if type(user) == User:
                return Notification.objects.filter(target_user=user)
            else:
                return []
        else:
            user = self.request.user
            if type(user) == User:
                return Notification.objects.filter(target_user=user)
            else:
                return []