from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView
from rest_framework.views import APIView
from atlima_django.users.api.serializers import PrivacySerializer
from atlima_django.common.models import PrivacySetting
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from atlima_django.common.models import ConfirmationActivity
from atlima_django.common.api.utils import generate_code_4d
from atlima_django.common.api.smsc import SMSC
from django.db.models import Q
from atlima_django.common.models import Organizer, OrganizerAdministration
import json 
from rest_framework.authentication import (SessionAuthentication, 
                                           BasicAuthentication, 
                                           TokenAuthentication)
from atlima_django.sport_events.models import Event
from rest_framework.permissions import IsAuthenticated
from atlima_django.users.api.serializers import UserSerializer
from django.db.models import CharField
from transliterate import translit
from django.db.models.functions import Lower

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        assert (
            self.request.user.is_authenticated
        )  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()



# НАСТРОЙКИ КОНФИДЕНЦИАЛЬНОСТИ (СОЗДАЮТСЯ ПРИ РЕГЕ)
class PersonalSettingsView(APIView):

    def get(self, request):
        user = request.user
        serializer = PrivacySerializer
        if type(user) == User:
            privacy_settings = PrivacySetting.objects.get_or_create(user=user)
            serialized = serializer(privacy_settings).data
        else:
            serialized = []

        return JsonResponse(serialized)

    def put(self, request):
        data = request.data
        request_user = request.user
        
        privacy_settings = PrivacySetting.objects.get_or_create(user=request_user)
        
        phone_visibility = data.get('phone_visibility')
        email_visibility = data.get('email_visibility')
        want_to_get_mails_from_atlima = data.get('want_to_get_email_from_atlima')
        who_can_send_messages = data.get('who_can_send_messages')
        blocked = data.get('blocked')

        # если есть уже существующие настройки конфиденциальности
        if privacy_settings:
            # видимость телефонного номера
            if phone_visibility and phone_visibility in (PrivacySetting.ALL, PrivacySetting.ONLY_SUBSCRIBERS, PrivacySetting.ONLY_ME):
                privacy_settings.phone_visibility = phone_visibility
            
            # видимость электронной почты
            if email_visibility and email_visibility in (PrivacySetting.ALL, PrivacySetting.ONLY_SUBSCRIBERS, PrivacySetting.ONLY_ME):
                privacy_settings.email_visibility = email_visibility
            
            # получение рассылки от Атлимы
            if want_to_get_mails_from_atlima:
                privacy_settings.want_to_get_mails_from_atlima = want_to_get_mails_from_atlima

            # кто может посылать сообщения
            if who_can_send_messages and who_can_send_messages in (PrivacySetting.ALL, PrivacySetting.ONLY_SUBSCRIBERS, PrivacySetting.ONLY_ME):
                privacy_settings.who_can_send_messages = who_can_send_messages
    
            # массив заблокированных пользователей
            if blocked:
                privacy_settings.blocked.clear()
                for user_id in blocked:
                    try:
                        user = User.objects.get(id=user_id)
                        privacy_settings.blocked.add(user)
                    except:
                        pass

            privacy_settings.save()
        else:
            return JsonResponse({"status": False, "message": "FATAL: No privacy settings!!!"}, status=404)    
        return JsonResponse({"status": True})


# СБРОС ПАРОЛЯ
class PasswordReset(APIView):
    """Сброс пароля и установка нового"""
    authentication_classes = [TokenAuthentication]
    def post(self, request):
        data = request.data
        phone = data['phone']
        code = data['code']
        new_password = data.get('password')

        if new_password is not None:
            confirmation = ConfirmationActivity.objects.filter(status=0, 
                                                                data=code, 
                                                                target=phone, 
                                                                action='password_reset').last()
            if confirmation is None:
            
                return JsonResponse({"status": False, "errors": {"code": ["code and phone not found"]}}, status=400)
            
            else:
            
                user = User.objects.get(username=phone)
                user.set_password(new_password)
                user.save()

                confirmation.status = 1
                confirmation.save()
        else:
            confirmation = ConfirmationActivity.objects.filter(status=0, 
                                                                data=code, 
                                                                target=phone, 
                                                                action='password_reset').last()
            if confirmation is None:
                return JsonResponse({"status": False, "errors": {"code": ["code and phone not found"]}}, status=400)
            else:
                return JsonResponse({"status": True})
        
        return JsonResponse({"status": True})



# отправка кода подтверждения в СМС
class SMSPasswordReset(APIView):
    """Отправка кода подтверждения номера телефона пользователю"""
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        received_json_data = json.loads(request.body)
        user = request.user

        try:
            phone = received_json_data['phone']
        except KeyError:
            return JsonResponse({"status": False, 
                                "errors": {"phone": ['cant be null']}}, 
                                safe=False, 
                                status=400)        

        if phone.startswith('7') or phone.startswith('+7'):
            code = generate_code_4d()
            smsc_instance = SMSC()
            r = smsc_instance.send_sms(phone, code, sender="atlima")
            if len(r) == 4:
                response = {"status": True, "code": code}
                new_confirmation = ConfirmationActivity.objects.create(user=None,
                                                    action="password_reset",
                                                    data=code,
                                                    target=phone,
                                                    status=0)
                new_confirmation.save()
            else:
                response = {"status": False, "code": code}
            return JsonResponse(response)
        else:
            return JsonResponse({'status': False, "error": {'phone': ["wrong number format"]}}, safe=False, status=400)
    
    
# Поиск пользователя по имени (общий)
class SearchUserByName(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        data = request.data
        CharField.register_lookup(Lower, 'lower')
        serializer = UserSerializer

        try:
            username = data['username']
            username = username.lower()
            username += ' '
            part_1, part_2 = username.split(' ')[0], username.split(' ')[1]
            tpart_1 = translit(part_1, language_code='ru', reversed=True)
            tpart_2 = translit(part_2, language_code='ru', reversed=True)

            users = User.objects.filter((Q(first_name__lower__icontains=part_1)&Q(last_name__lower__icontains=part_2)) | (Q(first_name__lower__icontains=part_2)&Q(last_name__lower__icontains=part_1))|(Q(first_name__lower__icontains=tpart_1)&Q(last_name__lower__icontains=tpart_2)) | (Q(first_name__lower__icontains=tpart_2)&Q(last_name__lower__icontains=tpart_1))).filter(is_active=True).all()

            if users is not None:
                serialized = serializer(users, many=True)
                return JsonResponse(serialized.data, safe=False)
            else:
                return JsonResponse([], safe=False)
        except KeyError:
            return JsonResponse({"status": False, "errors": {'username': ['username is required']}})


# ДОПОЛНИТЕЛЬНЫЕ КЛАССЫ ДЛЯ УПРАВЛЕНИЯ ОРГАМИ

class OrganizerAdministratorList(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request, organizer_id):
        try:
            organizer = Organizer.objects.get(id=organizer_id)
            organizer_administrators = OrganizerAdministration.objects.filter(organizer_record=organizer).all()
            organizer_admins = []

            for organizer_admin in organizer_administrators:
                record = {}
                id = organizer_admin.id
                user = organizer_admin.profile_record.user
                user_serializer = UserSerializer
                serialized_user = UserSerializer(user, context={'request': request})
                record['admin_id'] = id
                record['user'] = serialized_user.data
                organizer_admins.append(record)
            
            
            return JsonResponse(organizer_admins, safe=False)

        except ObjectDoesNotExist:
            return JsonResponse({"status": False})


class OrganizerAdministratorManagement(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, organizer_id, user_id):
        try:
            user = User.objects.get(id=user_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "user not found"}, status=404)

        try:
            organizer = Organizer.objects.get(id=organizer_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "organizer not found"}, status=404)
        
        check = OrganizerAdministration.objects.filter(organizer_record=organizer, profile_record=user).first()
        if check:
            return JsonResponse({"status": False, "errors": {"user": ["already admin"]}}, status=400)

        new_organizer_admin = OrganizerAdministration.objects.create(organizer_record=organizer, profile_record=user)
        new_organizer_admin.save()

        return JsonResponse({"status": True})


class OrganizerAdministratorDeletion(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def delete(self, request, user_id):
        admin_record = OrganizerAdministration.objects.get(id=user_id)
        admin_record.delete()
        return JsonResponse({"status": True})

