from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.views import APIView

from django.http import JsonResponse

from rest_framework import authentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import parser_classes
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated

from .serializers import UserSerializer, ProfileSerializer
from atlima_django.common.api.utils import create_system_event_object
from atlima_django.common.models import ConfirmationActivity

from rest_framework.authtoken.serializers import AuthTokenSerializer
from django.db.models import Q
import json
import re
from atlima_django.location.models import Country, Region, City
from atlima_django.sport_events.models import Event, Slot
from atlima_django.users.models import User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import CharField, Q
from django.db.models.functions import Lower
from transliterate import translit
from atlima_django.common.models import OrganizerAdministration
from atlima_django.sport.models import Sport, SportAdministrator
from atlima_django.sport_events.models import UserInterestedIn
from django.contrib.auth.password_validation import CommonPasswordValidator


User = get_user_model()


# просмотр информации о пользователе
class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "username"

    def get_queryset(self, *args, **kwargs):
        assert isinstance(self.request.user.id, int)
        return self.queryset.filter(id=self.request.user.id)

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    
# получение информации по профилю пользователя
class GetMyProfileInfo(APIView):
    """
    Returns information about current user.
    **Logic**
    View check Accept-Language in header(en-us, ru-ru), get right serializer
    and return result.
    **Returns**
    Serialized Profile object.
    """
    authentication_classes = [TokenAuthentication,]
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        user = request.user
        serializer = ProfileSerializer
        token, created = Token.objects.get_or_create(user=user)
        profile = User.objects.filter(id=user.id).first()
        serialized = serializer(profile, context={'request', request})
        data = serialized.data
        return JsonResponse(data, safe=False)


# авторизация в систему
class Signin(APIView):
    serializer_class = AuthTokenSerializer

    def get_serializer(self, *args, **kwargs):
        
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        # try:
        body = request.body
        serializer = self.get_serializer(data=request.data)
        check = serializer.is_valid(raise_exception=False)
        if check is False:
            return JsonResponse({"status": False, "errors": {"user": ["wrong credentials"]}}, status=400)

        user = serializer.validated_data['user']

        token, created = Token.objects.get_or_create(user=user)
        
        profile = User.objects.get(id=user.id)
        profile_serializer = ProfileSerializer
        serialized = profile_serializer(profile).data

        # системное событие при авторизации пользователя
        try:
            create_system_event_object(request.user, 'user_authorized', {"id": user.id})
        except:
            pass

        return JsonResponse(serialized)


# смена пароля пользователя    
class ChangeUserPassword(APIView):
    """Change user password"""

    authentication_classes = [TokenAuthentication,]
    permission_classes = [IsAuthenticated, ]

    def post(self, request):
        received_json_data = json.loads(request.body)
        user = request.user
        try:
            old_password = received_json_data['old_password']
        except KeyError:
            return JsonResponse({"status": False}, status=400)

        if user.check_password(old_password):
            try:
                new_password = received_json_data['new_password']
                if new_password == old_password:
                    return JsonResponse({"status": False, 
                                         "message": "Passwords is identical, not updated"})
                user.set_password(new_password)
                user.save()
                
                # изменены данные пользователя
                try:
                    create_system_event_object(user, 'user_changed', 
                                               {'id': user.id})
                except:
                    pass

                return JsonResponse({"status": True})
            except KeyError:
                return JsonResponse({"status": False, 
                                     "message": "No required parameter (new_password)"}, 
                                    status=400)
        else:
            return JsonResponse({"status": False, 
                                 "message": "Wrong password"}, 
                                status=401)


# проверка пользователя на существование
class CheckUserExists(APIView):
    def post(self, request):
        data = request.data
        input_username = data.get('username')
        user_response_username_check = User.objects.filter(
            username=input_username
            ).first()
        if not user_response_username_check:
            return JsonResponse({"status": False})
        return JsonResponse({"status": True})


# создание нового пользователя
class CreateUserWithProfile(APIView):
    """
        Creates User with profile Atlima User.
        All fields are required.
        Create object for User with fields:
        - last_name
        - first_name
        - username as phone_number
        - email
        - password (with default hashing)

        Create object for AtlimaUser with fields:
        - first_name_transliterated
        - last_name_transliterated
        - birth_date
        - phone
    """

    def post(self, request):
        received_json_data = json.loads(request.body)
        error = {}
        last_name = received_json_data.get('last_name')
        first_name = received_json_data.get('first_name')
        native_firstname = received_json_data.get('native_firstname')
        native_lastname = received_json_data.get('native_lastname')
        sex = received_json_data.get('sex')
        email = received_json_data.get('email')
        phone_number = received_json_data.get('phone')
        birth_date = received_json_data.get('birth_date')
        password = received_json_data.get('password')

        code = received_json_data.get("code")
        
        if last_name is None: error["last_name"] = ["last_name required"]
        if first_name is None: error["first_name"] = ["first_name required"]
        if native_firstname is None: error["native_firstname"] = ["native_firstname required"]
        if native_lastname is None: error["native_lastname"] = ["native_lastname required"]
        if sex is None: error["sex"] = ["sex required"]
        if email is None: error["email"] = ["email required"]
        if phone_number is None: error["phone"] = ["phone required"]
        if birth_date is None: error["birth_date"] = ["birth_date required"]
        if password is None: error["password"] = ["password required"]

        if last_name is not None: last_name = last_name.strip()
        if first_name is not None: first_name = first_name.strip()
        if email is not None: email = email.strip()
        if native_firstname is not None: native_firstname = native_firstname.strip()
        if native_lastname is not None: native_lastname = native_lastname.strip()
        if phone_number is not None: phone_number = phone_number.strip()
        if password is not None: password = password.strip()

        if last_name == "": error["last_name"] = ["last_name cant be empty"]
        if first_name == "": error["first_name"] = ["first_name cant be empty"]
        if email == "": error["email"] = ["email cant be empty"]
        if native_firstname == "": error["native_firstname"] = ["native_firstname cant be empty"]
        if native_lastname == "": error["native_lastname"] = ["native_lastname cant be empty"]
        if phone_number == "": error["phone"] = ["phone cant be empty"]
        if password == "": error["password"] = ["password cant be empty"]

        # проверяем телефон и электронную почту только для активных пользователей
        if phone_number is not None:
            check_phone_is_used = User.objects.filter(username=phone_number, is_active=True).first()
            if check_phone_is_used is not None:
                error['phone'] = ['phone is used by another user']

        if email is not None:
            check_email_is_used = User.objects.filter(Q(email=email)&~Q(id=request.user.id)&Q(is_active=True)).first()
            if check_email_is_used is not None:
                error['email'] = ['email is used by another user']
        
        if first_name is not None and first_name != "":
            latin = first_name.isascii()
            if latin is False:
                error['first_name'] = ['first_name must be latin']
        
        if last_name is not None and last_name != "":
            latin = last_name.isascii()
            if latin is False:
                error['last_name'] = ['last_name must be latin']

        if birth_date is not None and birth_date != "":
            from datetime import datetime as datemod
            now = datemod.now().date()
            birth_date = datemod.strptime(birth_date, "%Y-%m-%d").date()
            if birth_date >= now:
                error['birth_date'] = ['birth_date is wrong: must be less then today']

        if len(error) > 0:
            return JsonResponse({"status": False, "errors": error}, safe=False, status=400)

        if code is None:
            return JsonResponse({"status": True, "message": "validation completed succesfully"})
        else:
            new_confirmation = ConfirmationActivity.objects.filter(
                target=phone_number, 
                data=code, 
                action='phone_confirmation', 
                status=0
                ).first()
    
            if new_confirmation is not None:
                new_confirmation.status = 1
                new_confirmation.save()
            else:
                return JsonResponse({"status": False, 
                                     "errors": {"code": [f"no confirmation with code {code} for phone {phone_number}"]}}, 
                                    status=404)

        phone_number = re.sub("[^0-9]", "", phone_number)

        # если все переданные данные ок, создаём пользователя и профиль
        user = User.objects.create_user(username=phone_number,
                                        password=password,
                                        first_name=first_name,
                                        last_name=last_name,
                                        email=email)

        atlima_profile = User.objects.create(user=user,
                                            sex=sex,
                                            birth_date=birth_date,
                                            native_firstname=native_firstname,
                                            native_lastname=native_lastname,
                                            phone=phone_number)
        atlima_profile.save()


# удаление фото пользователя
class DeleteProfilePhoto(APIView):
    """Delete profile photo from user:
    current model on_delete installed to SET_NULL: after deleting field profile_image is None

    """

    authentication_classes = [SessionAuthentication,]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = User.objects.filter(user=request.user)
        try:
            current_profile_photo = user.profile_photo
            current_profile_photo.clear()
            # пользователь внёс изменения, создаём системное событие
            try:
                create_system_event_object(request.user, 'user_changed', {"id": user.id})
            except:
                pass
            return JsonResponse({"status": True})
        except Exception:
            return JsonResponse({"status": False, 
                                 "message": "Error during deleting profile image"}, status=400)
            

# добавление фото пользователя
class AddProfilePhoto(APIView):
    """POST image data to model:
    from multipart-form data load image to profile photo instance (field=photo)
    delete previous instance from database and filesystem (with free atlima_user)
    add new photo to atlima_user and save it as reference"""
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            data = request.data['photo']
            user.photo = data
            user.save()
            # вносим изменения в пользователя - добавляем системное событие
            try:
                create_system_event_object(request.user, 'user_changed', {"id": user.id})
            except:
                pass
            return JsonResponse({"status": True})
        except KeyError as error:
            return JsonResponse({"status": False, "message": "Failed, error: no parameters (form-data photo)"}, status=400)
        except Exception as e:
            return JsonResponse({"status": f"Error during loading to server: {e}"}, safe=False, status=403)
        
        
# Добавление информации в профиль пользователя     
class AddUserInformation(APIView):
    """
        Update for user (add country, city and email information by provided username).
        All fields are optional.
        For object User updates field email.
        For object AtlimaUser updates fields country and city (temporary charfields).
    """
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        data = request.data

        user = request.user

        # input data about atlima user
        country = data.get('country')
        if country is not None:
            country_ref = Country.objects.filter(id=country).first()
            if country_ref:
                user.country = country_ref
            else:
                return JsonResponse({"status": False, "message": 'No country with provided ID'}, status=404)

        region = data.get('region')

        if region is not None:
            region_ref = Region.objects.filter(id=region).first()
            if region_ref:
                user.region = region_ref
            else:
                return JsonResponse({"status": False, "message": 'No region with provided ID'}, status=404)

        city = data.get('city')
        if city is not None:
            city_ref = City.objects.filter(id=city).first()
            if city_ref:
                user.city = city_ref
            else:
                return JsonResponse({"status": False, "message": 'No city with provided ID'}, status=404)

        first_name = data.get('first_name')
        if first_name is not None:
            user.first_name = first_name

        last_name = data.get('last_name')
        if last_name is not None:
            user.last_name = last_name

        patronym = data.get('patronym')
        if patronym:
            user.patronym = patronym

        native_firstname = data.get(
            'native_firstname')
        native_lastname = data.get(
            'native_lastname')
        native_patronym = data.get('native_patronym')

        if native_lastname is not None:
            user.native_lastname = native_lastname
        if native_firstname is not None:
            user.native_firstname = native_firstname
        if native_patronym is not None:
            user.native_patronym = native_patronym

        birth_date = data.get('birth_date')
        if birth_date:
            user.birth_date = birth_date

        alias = data.get('alias')
        if alias:
            user.alias = alias

        phone = data.get('phone')
        if phone:
            user.phone = phone

        sex = data.get('sex')
        if sex:
            if sex in ('M', 'F'):
                user.sex = sex
            else:
                return JsonResponse({"status": False, "message": 'Sex must be M or F'}, status=400)

        fb_profile = data.get('fb_profile')
        if fb_profile:
            user.fb_profile = fb_profile
        vk_profile = data.get('vk_profile')
        if vk_profile:
            user.vk_profile = vk_profile
        instagram_profile = data.get('instagram_profile')
        if instagram_profile:
            user.instagram_profile = instagram_profile

        strong_hand = data.get('strong_hand')
        if strong_hand is not None: user.strong_hand = strong_hand

        user.save()
        user.save()

        # отправляем системное событие
        try:
            create_system_event_object(user, 'user_changed', {"id": user.id})
        except: 
            pass 

        profile = User.objects.get(user=user)

        serializer = ProfileSerializer
        serialized = serializer(profile)

        return JsonResponse(serialized.data, safe=False)
    

# администраторы платформы
class PlatformAdministrators(APIView):

    def get(self, request):
        """Администраторами платформы становятся с
        флагами is_staff и is_superadmin"""
        users = User.objects.filter(Q(is_active=True)
                                    &(Q(is_staff=True)
                                    |Q(is_superuser=True))).all()
        serializer = UserSerializer
        serialized = serializer(users, many=True, context={'request': request})
        data = serialized.data

        return JsonResponse(data, safe=False)
    
    
    
class SearchUserByNameForEventAdministration(APIView):
    """Поиск пользователя по имени для назначения 
    администратором события"""
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, event_id):
        data = request.data
        CharField.register_lookup(Lower, 'lower')
        serializer = UserSerializer
        try:
            event = Event.objects.get(id=event_id)
            #
            event_admins = Event.objects.values_list('user', flat=True).distinct()
            #
            
            event_admins = User.objects.filter(id__in=event_admins).values_list('user', flat=True)
            not_event_admins = User.objects.filter(~Q(id__in=event_admins))

            event_participants = Slot.objects.filter(event=event, paid=True, active=True).values_list('user', flat=True).distinct()
            not_event_participants = not_event_admins.filter(~Q(id__in=event_participants))

            searched = data['username']
            searched = searched.lower()
            active_users = not_event_participants.filter(is_active=True)
            users = active_users.filter(Q(first_name__lower__icontains=searched)|Q(last_name__lower__icontains=searched)).all()

            if users is not None:
                serialized = serializer(users, many=True)
                return JsonResponse(serialized.data, safe=False)
            else:
                return JsonResponse([], safe=False)
        except KeyError:
            return JsonResponse({"status": False, "errors": {'username': ['username is required']}})
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {'event_id': ['event not found!']}}, status=404)
        
        
        
class SearchUserByNameForOrganizerAdministration(APIView):
    """Поиск пользователя по имени для назначения администратором
    организатора. Исключает текущих админов из поиска."""
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, organizer_id):
        data = request.data
        CharField.register_lookup(Lower, 'lower')
        serializer = UserSerializer

        try:
            organizer_admins = OrganizerAdministration.objects.filter(organizer_record__id=organizer_id).values_list('profile_record', flat=True).distinct()
            users_to_exclude = User.objects.filter(id__in=organizer_admins).values_list('user', flat=True).distinct()
            admin_users = User.objects.filter(id__in=users_to_exclude).values_list('id', flat=True).distinct()

            username = data['username']
            username = username.lower()
            username += ' '
            part_1, part_2 = username.split(' ')[0], username.split(' ')[1]
            tpart_1 = translit(part_1, language_code='ru', reversed=True)
            tpart_2 = translit(part_2, language_code='ru', reversed=True)

            users = User.objects.filter((Q(first_name__lower__icontains=part_1)&Q(last_name__lower__icontains=part_2)) | (Q(first_name__lower__icontains=part_2)&Q(last_name__lower__icontains=part_1))|(Q(first_name__lower__icontains=tpart_1)&Q(last_name__lower__icontains=tpart_2)) | (Q(first_name__lower__icontains=tpart_2)&Q(last_name__lower__icontains=tpart_1))).filter(is_active=True).all()

            users = users.filter(~Q(id__in=admin_users))

            if users is not None:
                serialized = serializer(users, many=True)
                return JsonResponse(serialized.data, safe=False)
            else:
                return JsonResponse([], safe=False)
        except KeyError:
            return JsonResponse({"status": False, "errors": {'username': ['username is required']}})
        
        
        
# Смена организатора вида спорта
class ChangeAdminStatusV2(APIView):

    def put(self, request, sport_admin_id):
        data = request.data
        admin = SportAdministrator.objects.get(id=sport_admin_id)

        is_referee_collegium_member = data.get('is_referee_collegium_member')
        is_referee_collegium_president = data.get('is_referee_collegium_president')
        
        # нельзя одновременно установить оба флага
        if is_referee_collegium_member and is_referee_collegium_president:
            return JsonResponse({"status": False, "errors": {"is_referee_collegium": ["cant be both"]}}, status=400)

        # нельзя установить флаг председателя, если пользак член коллегии судей
        if admin.is_referee_collegium_member and is_referee_collegium_president and is_referee_collegium_member is not False:
            return JsonResponse({"status": False, "errors": {"is_referee_collegium": ["collegium member already"]}}, status=400)

        # нельзя установить флаг члена коллегии судей, если пользак председатель коллегии судей
        if admin.is_referee_collegium_president and is_referee_collegium_member and is_referee_collegium_president is not False:
            return JsonResponse({"status": False, "errors": {"is_referee_collegium": ["collegium president already"]}}, status=400)
        
        # проверяем полученные значения и устанавливаем флаги
        admin.is_referee_collegium_member = is_referee_collegium_member if is_referee_collegium_member is not None else admin.is_referee_collegium_member
        admin.is_referee_collegium_president = is_referee_collegium_president if is_referee_collegium_president is not None else admin.is_referee_collegium_member
        
        admin.save()


# РАЗЖАЛОВАНИЕ АДМИНИСТРАТОРА ВИДА СПОРТА
class DeleteSportAdministratorV2(APIView):
    
    """
        Разжалование пользователя из администраторов спорта
    """
    
    def put(self, request, sport_admin_id):
        try:
            sport_admin = SportAdministrator.objects.get(id=sport_admin_id)
            user = sport_admin.user
            if sport_admin.region is None:
                admin_country = sport_admin.country
                sport_admins_by_country = SportAdministrator.objects.filter(country=admin_country,
                                                                            region__isnull=True).all()
                if sport_admins_by_country.count() > 1:
                    sport_admin.delete()
                else:
                    return JsonResponse({"status": False, "errors": {"admin": ["last admin for this country"]}}, status=400)
            else:
                sport_admin.delete()
            # создаём системное событие на удаление пользователя из администраторов
            create_system_event_object(request.user, 'user_sport_type_permission_removed', {"id": sport_admin_id,       "target_user": user.id})

            return JsonResponse({"status": True})
        except ObjectDoesNotExist:
            pass

        return JsonResponse({"status": False}, status=400)


# Добавление нового организатора спорта
class AddSportAdminV2(APIView):

    def post(self, request, sport_id):

        data = request.data

        user_id = data['user_id']

        try:
            user = User.objects.get(id=user_id)
        except ObjectDoesNotExist:
            return JsonResponse({'status': False, "message": "User not found"}, safe=False, status=404)

        try:
            sport = Sport.objects.get(id=sport_id)
        except ObjectDoesNotExist:
            return JsonResponse({'status': False, 'message': 'Object does not exists'}, safe=False, status=404)

        country_id = data['country_id']

        try:
            country = Country.objects.get(id=country_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "No country with provided ID"}, safe=False, status=400)

        region = data.get('region_id')

        if region:
            try:
                region = Region.objects.get(id=region)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "message": "No region with provided ID"}, safe=False, status=400)


        is_user_in_administrator_list = SportAdministrator.objects.filter(sport=sport,
                                                                        user=user,
                                                                        country=country,
                                                                        region=region).first()
        if not is_user_in_administrator_list:
            if region:
                # страна и регион
                is_referee_collegium_member = data.get('is_referee_collegium_member')
                is_referee_collegium_president = data.get('is_referee_collegium_president')

                if is_referee_collegium_member is None: is_referee_collegium_member = False
                if is_referee_collegium_president is None: is_referee_collegium_president = False

                delegation = SportAdministrator.objects.create(sport=sport,
                                                                    country=country,
                                                                    region=region,
                                                                    user=user,
                                                                    is_referee_collegium_member=is_referee_collegium_member,
                                                                    is_referee_collegium_president=is_referee_collegium_president)
                delegation.save()
            else:
                # если есть страна, нет региона
                is_sks_member = data.get('is_sks_member')
                is_sks_president = data.get('is_sks_president')

                if is_sks_member is None: is_sks_member = False
                if is_sks_president is None: is_sks_president = False

                delegation = SportAdministrator.objects.create(sport=sport,
                                                                    country=country,
                                                                    user=user,
                                                                    is_sks_member=is_sks_member,
                                                                    is_sks_president=is_sks_president)
                delegation.save()
            serializer = self.get_serializer_class(request=request)
            serialized = serializer(delegation, context={'request': request})

            # добавляем системное событие при добавлении вида спорта
            try:
                create_system_event_object(request.user, 'user_sport_type_permission_added', {"id": delegation.id, "target_user": user_id})
            except: # noqa
                pass
            return JsonResponse(serialized.data, safe=False)
        else:
            return JsonResponse({"status": False, "message": "User already administrate this sport!"}, status=400)



# СПИСОК ЗАИНТЕРЕСОВАННЫХ В СОБЫТИИ ПОЛЬЗАКОВ
class UserInterestedInList(APIView):
    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, 
                                "errors": {'event': ['event not found']}}, 
                                status = 404)
        
        user_interested_in = event.interested.all()
        interested_in_list = user_interested_in.objects.add (user_interested_in)

        for user in interested_in_list:

            item = {}
            item['user_id'] = user.id
            item['username'] = f"{user.first_name} {user.last_name}"
            if user is not None:
                if user.photo:
                    item['photo'] = user.photo.url
                else:
                    item['photo'] = None
            else:
                item['photo'] = None
            user_interested_in.append(item)
        
        return JsonResponse(user_interested_in, safe=False)


class UserInterestedInEvent(APIView):

    authentication_classes = [TokenAuthentication]

    def post(self, request, event_id):
        """Создать новую запись заинтересованного пользователя"""
        user = request.user

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False,
                                "errors": {"event": ["not found"]}},
                                status=404)

        check = UserInterestedIn.objects.filter(user=user, event=event).first()

        if check is None:
            new_interested = UserInterestedIn.objects.create(user=user, event=event)
            new_interested.save()
            return JsonResponse({"status": True})
        else:
            return JsonResponse({"status": False,
                                "errors": {"interested": ["already"]}},
                                status=404)

    def delete(self, request, event_id):
        """удаление пользователя из заинтересованных"""
        user = request.user

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False,
                                "errors": {"event": ["not found"]}},
                                status=404)

        check = UserInterestedIn.objects.filter(user=user, event=event).first()

        if check is not None:
            check.delete()
            return JsonResponse({"status": True})
        else:
            return JsonResponse({"status": False,
                                "errors": {"not_interested": ["interested flag not found"]}},
                                status=404)



class PasswordPolicy(APIView):
    """Не менее 6 символов и не входит в распространенные пароли"""
    def post(self, request):
        data = request.data
        
        try:
            password = data['password']
        except KeyError:
            return JsonResponse({"status": False, "message": "password is required"}, 400)

        if len(password) < 9:
            common_password_validator = CommonPasswordValidator()
            try:
                check = common_password_validator.validate(password)
            except ValidationError:
                return JsonResponse({"status": False})

        return JsonResponse({"status": True})