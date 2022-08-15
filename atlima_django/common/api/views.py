from rest_framework.views import APIView
from atlima_django.common.models import Organizer
from atlima_django.common.api.serializers import OrganizerMenuSerializer
from django.http import JsonResponse
from rest_framework.authentication import (SessionAuthentication, 
                                           BasicAuthentication, 
                                           TokenAuthentication)
from rest_framework.permissions import IsAuthenticated
import json
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.location.models import Country, Region, City
from django.conf import settings
from atlima_django.common.api.utils import create_system_event_object
from atlima_django.sport_events.models import Event
from django.db.models.functions import Lower
from atlima_django.common.models import Complain
from atlima_django.system.models import SystemObject
from atlima_django.users.models import User
from atlima_django.common.api.serializers import ComplainSerializer
from rest_framework.pagination import LimitOffsetPagination
from rest_framework import mixins, generics
from atlima_django.users.api.serializers import UserSerializer
from atlima_django.common.api.serializers import OrganizerSerializer
from django.db.models import CharField, Q
from atlima_django.common.models import ConfirmationActivity
from atlima_django.common.api.utils import generate_code_4d
from atlima_django.common.models import EmailTemplate, Organizer, OrganizerAdministration
from atlima_django.common.api.serializers import OrganizerDraftSerializer
from atlima_django.sport.models import Sport
from rest_framework.generics import UpdateAPIView
import urllib
from utils import get_email_template_content, get_template_content, send_mail

# просмотр списка организаторов
class Organizers(APIView):

    def get(self, request):
        organizers_list = Organizer.objects.all()
        serializer = OrganizerMenuSerializer
        serialized = serializer(organizers_list, many=True, context={"request": request})
        result = serialized.data
        return JsonResponse(result, safe=False, status=200)
    

# создание адмнистратора
class OrganizerCreation(APIView):

    """Создание организатора с проверками на существование связанных сущностей"""
    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def post(self, request):
        if request.version == "1.0" or request.version is None:
            received_json_data = json.loads(request.body)
            
            # все поля, кроме логотипа, получаем здесь, все обязательные
            mandatory_fields = ('site', 'slug', 'country', 'region', 'city', 'location', 'descriptions')
            try:
                site = received_json_data['site']
                slug = received_json_data['slug']
                country = received_json_data['country_id']
                region = received_json_data['region_id']
                city = received_json_data['city_id']
                location = received_json_data['location']
            except KeyError:
                fields = ','.join(mandatory_fields)
                message = f"Mandatory fields : {fields}"
                return JsonResponse({"status": False, "message": message}, status=400)

            # наш слаг должен быть уникальным
            try:
                Organizer.objects.get(slug=slug)
                return JsonResponse({"status": False, "message": "This slug is already exists"}, status=400)
            except ObjectDoesNotExist:
                pass

            # получаем объекты (страну, регион и город), выдаём ошибку, если не находим по id
            try:
                country = Country.objects.get(id=country)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "message": "invalid country_id"}, status=400)

            try:
                region = Region.objects.get(id=region)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "message": "Incorrect region_id"}, status=400)

            try:
                city = City.objects.get(id=city)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "message": "Incorrect city"}, status=400)

            phone = received_json_data.get('phone')
            email = received_json_data.get('email')

            slug = slug.strip()

            # сохраняем нового Организатора, присваиваем ему все нужные атрибуты
            new_organizer = Organizer.objects.create(site=site, 
                                                    slug=slug, 
                                                    country=country, 
                                                    region=region, 
                                                    city=city, 
                                                    location=location,
                                                    phone=phone,
                                                    email=email)
            photo = received_json_data.get('photo')
            if photo:
                new_organizer.photo = photo
            new_organizer.save()

            # Закидываем создателя организатора в админы организаторов
            user = request.user
            
            admin_organizers = new_organizer.administrators
            admin_organizers.add(user)
            
            # descriptions and titles in multilingual
            descriptions = received_json_data['descriptions']
            for description in descriptions:
                language = description['language_id']
                organizer_title = description['title']
                description = description['description']
                
                languages = settings.LANGUAGES
                for i, language_content in (enumerate(languages)):
                    if i == language:
                        code = language_content[0]
                        new_organizer.set_current_language(code)
                        new_organizer.title = organizer_title
                        new_organizer.description = description
                            
            new_organizer.save()
            # создаём системное событие для добавленного организатора
            try:
                create_system_event_object(request.user, 'organizer_add', {'id': new_organizer.id})
            except:
                pass

            return JsonResponse({"status": True, "id": new_organizer.id})


# Списки системных языков
class SystemLanguages(APIView):

    def get(self, request):
        languages = settings.LANGUAGES
        items = []
        for index, language in languages:
            item = {}
            item['id'] = index
            item['code'] = language[0]
            item['description'] = language[1]
            items.append(item)
        result = {}
        result['languages'] = items
        return JsonResponse(result, safe=False)


# Список жалоб с фронтенда
class ComplainsList(generics.ListAPIView, mixins.CreateModelMixin):

    queryset = Complain.objects.all().order_by('-status', 'id')
    pagination_class = LimitOffsetPagination
    serializer_class = ComplainSerializer
    authentication_classes = [TokenAuthentication]

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _create_new_complain(self, request):
        data = request.data
        user = request.user
        user_ip = self._get_client_ip(request=request)

        if type(user) != User:
            user = None

        try:
            object_type = data['object_type']
            object_id = data['object_id']
            reason = data['reason']
        except KeyError as ke:
            err = str(ke)
            return 'error', {"status": False, "errors": {f"{err}": ["required"]}}
        try:
            object_type = SystemObject.objects.get(id=object_type)
        except ObjectDoesNotExist:
            return 'error', {"status": False, "errors": {"object_type": ["not found"]}}
        
        if reason not in range(1, 7):
            return 'error', {"status": False, "errors": {"reason": ["must be 1-6"]}}
        
        new_complain = Complain.objects.create(object_type=object_type,
                                                object_id=object_id,
                                                reason=reason,
                                                user=user,
                                                user_ip=user_ip)
        new_complain.save()

        status = 'ok'
        return status, new_complain.id
        
    def post(self, request):

        status, complain = self._create_new_complain(request=request)
        if status == 'ok':
            return JsonResponse({"status": True, "id": complain})
        else:
            return JsonResponse(complain)


    
# модерация жалоб
class ComplainsModerate(ComplainsList, APIView):

    authentication_classes = [TokenAuthentication]
    
    def _get_complain(self, complain_id):
        try:
            complain = Complain.objects.get(id=complain_id)
        except ObjectDoesNotExist:
            complain = None
        return complain

    def _update_complain(self, request, complain, status, moderator):
        complain.status = status
        complain.moderator = moderator
        complain.moderator_ip = self._get_client_ip(request=request)
        complain.save()

    def _set_accepted_declined(self, complain_id, moderator, request):
        data = request.data
        status = data['status']
        if status not in (1,2):
            status = None

        if status is not None:
            complain = self._get_complain(complain_id=complain_id)
            if complain:
                self._update_complain(request, complain, status, moderator)
                return True
            return False        

    def put(self, request, complain_id):
        user = request.user
        if type(user) != User:
            user = None

        result = self._set_accepted_declined(complain_id=complain_id, moderator=user, request=request)
        return JsonResponse({"status": result})


# Администраторы организатора
class OrganizerAdmins(APIView):

    def get(self, request, organizer_id):
        serializer = UserSerializer

        try:
            org = Organizer.objects.get(id=organizer_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"organizer_id": ["not found"]}}, status=404)
        
        admins = Organizer.objects.filter(organizer_record=org).values_list('profile_record', flat=True).distinct()
        profiles = User.objects.filter(id__in=admins).values_list('user', flat=True).distinct()
        users = User.objects.filter(id__in=profiles).all()

        serialized = serializer(users, many=True)
        data = serialized.data

        return JsonResponse(data, safe=False)


# организаторы, отфильтрованные по администратору
class OrganizerFilteredByAdmin(APIView):

    def get(self, request):
        serializer = OrganizerSerializer
        user = request.user
        if type(user) == User:
            profile = User.objects.get(user=user)
        
        if profile is not None:
            organizers = Organizer.objects.filter(
                profile_record=profile
                ).values_list('organizer_record', flat=True).distinct()
            orgs = Organizer.objects.filter(id__in=organizers)

            organizers_list = serializer(orgs, context={'request': request}, many=True)
            data = organizers_list.data
        else:
            data = []

        return JsonResponse(data, safe=False)


class CopyAdminsFromOrgToEvent(APIView):

    def post(self, request):
        data = request.data
        
        try:
            organizer_id = data['organizer_id']
            event_id = data['event_id']
        except KeyError as ke:
            error = str(ke)
            return JsonResponse({"status": False, "errors": {f"{error}":"is required"}}, status=400)

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event_id": ['not found']}}, status=404)

        try:
            organizer = Organizer.objects.get(id=organizer_id)
            admins = Organizer.objects.filter(organizer_record=organizer).values_list('profile_record', flat=True)
            profiles = User.objects.filter(id__in=admins).all()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"organizer_id": ['not found']}}, status=404)

        for profile in profiles:
            check = Event.objects.filter(user=profile).first()
            if check is None:
                new_admin = Event.objects.create(user=profile, event=event)
                new_admin.save()
        
        return JsonResponse({"status": True})


# получить список организаторов
class GetOrganizersListByIds(APIView):

    def post(self, request):
        data = request.data
        ids = data['ids']

        if ids is not None and ids != []:
            organizers = Organizer.objects.filter(id__in=ids).all()
        else:
            organizers = []

        if organizers != []:
            serializer = OrganizerSerializer
            serialized = serializer(organizers, context={"request": request}, many=True)

        return JsonResponse(serialized.data, safe=False)



# ПОИСК ОРГА ПО ИМЕНМИ
class SearchOrganizerByName(APIView):

    def get(self, request):
        serializer = OrganizerSerializer

        organizer_name = request.GET.get('search_term', '')
        organizer_name = organizer_name.lower()
        CharField.register_lookup(Lower, 'lower')

        # if source == 'name':
        if organizer_name is not None:
            city = City.objects.filter(Q(settlement__lower__icontains=organizer_name)|
                                        Q(english_name__lower__icontains=organizer_name)).values_list('id', flat=True)

            organizer = Organizer.objects.filter(title__lower__contains=organizer_name).values_list('related_organizer', flat=True)
            
            if organizer is not None:
                organizers = Organizer.objects.filter(id__in=organizer).all()
                serialized = serializer(organizers, context={'request': request}, many=True)
                data = serialized.data

                orgs_city = Organizer.objects.filter(city__id__in=city)
                if orgs_city.count() > 0:
                    serialized2 = serializer(orgs_city, many=True, context={'request': request})
                    data2 = serialized2.data
                    for item in data2:
                        data.append(item)
            else:
                data = []
        
        return JsonResponse(data, safe=False)
    
    
class GetConfirmationStatus(APIView):
    def get(self, request, contact):
        user = request.user
        data = request.data
        if contact is None: return JsonResponse({"status": False, "errors": {"contact": "contact is required"}})
        confirmation = ConfirmationActivity.objects.filter(user=user, target=contact, status=1).first()
        if confirmation is None: return JsonResponse({"status": False})
        return JsonResponse({"status": True})


class PhoneConfirmationAPI(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        user = request.user
        data = request.data
        
        try:
            phone = data['phone']
        except KeyError:
            return JsonResponse({"status": False, "errors": {'phone': ['phone is required']}}, status=400)

        try:
            code = data['code']
        except KeyError:
            return JsonResponse({"status": False, "errors": {'code': ['code is required']}}, status=400)

        if phone:
            try:
                check = User.objects.get(phone=phone)
            except ObjectDoesNotExist:
                check = None
        
        if check is not None:
            return JsonResponse({"status": False, "errors": {"phone": ['phone is used by other user']}}, status=403)


        new_confirmation = ConfirmationActivity.objects.filter(user=user, target=phone, data=code, action='phone_confirmation', status=0).first()
        
        if new_confirmation is not None:
            new_confirmation.status = 1
            new_confirmation.save()
            user.username = phone
            user.phone = phone
            user.save()
            user.save()
        else:
            return JsonResponse({"status": False, "message": f"no confirmation with code {code} for phone {phone}"}, status=404)
    
        return JsonResponse({"status": True})


class CheckPhoneRoute(APIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        data = request.data    
        user = request.user
        try:
            phone = data['phone']
            profile = User.objects.filter(phone=phone, active=True).first()
            if profile is not None:
                return JsonResponse({"status": True})
            else:
                return JsonResponse({"status": False})
        except KeyError:
            return JsonResponse({"status": False, "message": "phone is required"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False})
        
        
class SendMail(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        """Собираем письмо на лету, отправляем"""
        errors = {}

        user = request.user
        language = request.LANGUAGE_CODE
        # email = user.email
        data = request.data
        # код и параметры из реквеста, имя пользователя

        template_name = "email verification"
        email = data.get('email')

        if email:
            check = User.objects.filter(Q(email=email)&~Q(id=user.id)&Q(is_active=True)).first()
        
        if check is not None:
            errors['email'] = ["email is used by other user"]
            return JsonResponse({"status": False, "errors": errors}, status=403)

        code = generate_code_4d()
        params = data.get('params')

        if params is None: params = {}
        
        username = f"{user.first_name} {user.last_name}"

        # добавляем в параметры данные пользователя
        params.update({'code': code})
        params.update({'username': username})

        if template_name.lower() == "email verification":
            # сначала из переданных параметров получаем все нужные переменные
            template = EmailTemplate.objects.get(template_name='Email Verification')
            content = get_email_template_content(language, template)
            if content is not None:
                # добавлен тип для отправки email: title и message, они лежат в разных полях
                title_template = get_template_content(content.title_template_text, params)
                message_template = get_template_content(content.message_template_text, params)
            else:
                # return JsonResponse({"status": False, "message": "content not found"}, status=404)
                errors['template_name'] = ['template not found']
            # В РЕЗУЛЬТАТЕ ОТПРАВКИ ПОЛУЧАЕМ РЕЗУЛЬТАТ В ВИДЕ int (0 - 1)
            result = send_mail(title_template, message_template, 'info@atlima.ru', [email])
            # проверяем: если результат равен единице, значит, сообщение отправлено
            if result == 1:
                new_confirmation = ConfirmationActivity.objects.create(user=user, 
                                                        action="email_confirmation", 
                                                        data=code,
                                                        target=email,
                                                        status=0)
                new_confirmation.save()
            # в противном случае оповещаем о сбое при передаче
            else:
                errors['mail_server'] = ["problems with mail server (Yandex SMTP)"]
        else:
            errors['template_name'] = ["not implemented"]

        if len(errors) > 0:
            return JsonResponse({"status": False, "errors": errors}, safe=False, status=400)
        else:
            return JsonResponse({"status": True})


# ПРОВЕРКА СЛАГОВ
class CheckEventSlug(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication,]

    def get(self, request, slug):
        if request.version == "1.0" or request.version is None:
            events = Event.objects.filter(slug=slug).all()
            uniqness = events.count()
            if uniqness > 0:
                return JsonResponse({"unique": False})
            return JsonResponse({"unique": True})  


class CheckSportSlug(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication,]

    def get(self, request, slug):
        sports = Sport.objects.filter(slug=slug).all()
        uniqness = sports.count()

        if uniqness > 0:
            return JsonResponse({"status": True})
        
        return JsonResponse({"status": False})


class CheckOrganizerSlug(APIView):

    authentication_classes = [TokenAuthentication,]

    def get(self, request, slug):
        slug = urllib.unquote(slug)
        organizers = Organizer.objects.filter(slug=slug).all()
        if organizers:
            return JsonResponse({"unique": False})
        return JsonResponse({"unique": True})


class DeleteOrganizerAdmin(APIView):

        authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
        permission_classes = [IsAuthenticated,]

        def delete (self, request, organizer_id, user_id):
            try:
                user = User.objects.get(id=user_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, 
                                    "errors": {"user": ['not found']}}, 
                                    status=404)

            # получаем организатора 
            organizer = Organizer.objects.get(id=organizer_id)
            
            # ищем запись с такими параметрами в админке
            check = OrganizerAdministration.objects.all()
            check_count = check.count()
            # ищем запись с такими параметрами в админке
            try:
                organizer_administration = OrganizerAdministration.objects.get(organizer_record=organizer, profile_record=user)
                if check_count > 1:
                    organizer_administration.delete()
                else:
                    return JsonResponse({"status": False, "errors": {'admin': ['cant delete last admin!']}}, status=400)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "message": "no organizer admin record with provided parameters"})
            
            return JsonResponse({"status": True}, status=200)


class AddOrganizerAdmin(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, organizer_id):
        data = request.data
        user_profile= request.user

        try:
            organizer = Organizer.objects.get(id=organizer_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False,
                                "errors": {"organizer_id": "not found"}},
                                status=404)
        
        organizer_admins_count = OrganizerAdministration.objects.filter(organizer_record=organizer).count()
        if organizer_admins_count < 2:
            return JsonResponse({"status": False, "errors": {"admin": ['cant delete last administrator']}}, status=400)

        check = OrganizerAdministration.objects.filter(organizer_record=organizer,
                                                        profile_record = user_profile).first()

        if check is None:
            new_administration_record = OrganizerAdministration.objects.create(organizer_record=organizer, profile_record=user_profile)
            new_administration_record.save()
        else:
            return JsonResponse({"status": False, 
                                "errors": {"user": ["already admin that org"]}},
                                status = 400)

        try:
            create_system_event_object(request.user, 'organizer_admin_added', json_content={'id': organizer.id, 'target_user': user_profile.user.id})
        except: # noqa
            pass        
        
        return JsonResponse({"status": True})
    
    
# экран администрирования организаторов
class OrganizerAdministrationScreen(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        # выбрать все мероприятия в админке без повторений
        organizers_in_admin = OrganizerAdministration.objects.values_list('organizer_record', flat=True).distinct()
        language = self.get_language(request=request)
        items = []

        for organizer in organizers_in_admin:
            item = {}
            related_organizer = Organizer.objects.get(id=organizer)
            list_of_users_for_event = OrganizerAdministration.objects.filter(organizer_record=related_organizer).values_list('profile_record', flat=True).distinct()

            # указываем ID ивента
            item['organizer_id'] = organizer

            item['organizer_title'] = organizer.title
            item['description'] = organizer.description

            user_list = []
            # получаем все нужные данные для отображения списка пользователей-админов
            for user in list_of_users_for_event:
                user_item = {}
                admin_record = Organizer.objects.filter(organizer_record=related_organizer, profile_record=user).first()
                user_item['admin_id'] = admin_record.id
                serializer = UserSerializer
                serialized = serializer(user, context={'request': request})
                user_item['user'] = serialized.data

                user_list.append(user_item)
            
            item['admins'] = user_list
            items.append(item)
        
        result = {}
        result['organizer_admins'] = items

        return JsonResponse(result, safe=False)
