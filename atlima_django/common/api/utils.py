import random
from atlima_django.system.models import SystemEvent, SystemEventType
from atlima_django.notifications.models import Notification, NotificationTemplate
from atlima_django.users.models import User
import json
from django.http import JsonResponse
from atlima_django.common.models import ConfirmationActivity
from .smsc import SMSC
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.views import APIView
from pytz import timezone
import os
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse
from atlima_django.common.models import EmailTemplate


# генерация 4-значного цифрового кода
# для отправки пользователю. Используется в 
# подтверждениях
def generate_code_4d():
    code = random.randint(1000, 9999)
    return str(code)


# генерация системных событий для конкретного пользователя
def create_system_event_object(user, system_event_type, json_content=None):
    """Создание записи о системном событии"""
    # создаём запись о системном событии
    system_event_type_obj = SystemEventType.objects.get(title=system_event_type)
    new_system_event = SystemEvent.objects.create(user=user, system_type=system_event_type_obj,
                                                  json_attributes=json_content)
    new_system_event.save()

    try:
        # просматриваем все шаблоны уведомлений и в случае, если для этого типа события
        # он существует, создаём новое уведомление и посылаем его пользователю
        notification_template = NotificationTemplate.objects.get(system_event_type=system_event_type_obj)
        atlima_obj_type = system_event_type_obj.system_object
        
        try:
            atlima_obj_id = json_content['id']
        except KeyError:
            atlima_obj_id = None
        
        # если целевым пользователем является пользователь, отличный от инициатора, он есть в
        # списке переданных параметров
        try:
            target_user_from_params = json_content['target_user']
            target_user = User.objects.get(target_user_from_params)
        except KeyError:
            target_user = user

        notification = Notification.objects.create(atlima_obj_type=atlima_obj_type,
                                                   atlima_obj_id=atlima_obj_id,
                                                   target_user=target_user,
                                                   system_event=new_system_event,
                                                   notification_template=notification_template)
        notification.save()
    except:  # noqa
        pass


# Подтверждение телефона по СМС
class SMSConfirmationCodeSend(APIView):
    """Отправка кода подтверждения номера телефона пользователю"""

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]

    def post(self, request):
        data = request.data
        user = request.user

        try:
            phone = data['phone']
        except KeyError:
            return JsonResponse({"status": False, 
                                 "message": "Phone must be not null"}, 
                                safe=False, 
                                status=400)
        
        if phone.startswith('7') or phone.startswith('+7'):
            code = generate_code_4d()
            smsc_instance = SMSC()
            r = smsc_instance.send_sms(phone, code, sender="atlima")
            if len(r) == 4:
                response = {"status": True, "code": code}
                if type(request.user) == User:
                    new_confirmation = ConfirmationActivity.objects.create(user=request.user,
                                                        action="phone_confirmation",
                                                        data=code,
                                                        target=phone,
                                                        status=0)
                    new_confirmation.save()
                else:
                    new_confirmation = ConfirmationActivity.objects.create(user=None,
                                                        action="phone_confirmation",
                                                        data=code,
                                                        target=phone,
                                                        status=0)
                    new_confirmation.save()
            else:
                response = {"status": False, "code": code}
            return JsonResponse(response)
        else:
            return JsonResponse({'status': False, 
                                 "error": {'phone': ["wrong number format"]}}, 
                                safe=False, 
                                status=400)
            
            
@csrf_exempt
def upload_image(request):
    if request.method == "POST":
        file_obj = request.FILES['file']
        file_name_suffix = file_obj.name.split(".")[-1]
        if file_name_suffix not in ["jpg", "png", "gif", "jpeg", ]:
            return JsonResponse({"message": "Wrong file format"})

        upload_time = timezone.now()
        path = os.path.join(
            settings.MEDIA_ROOT,
            'tinymce',
            str(upload_time.year),
            str(upload_time.month),
            str(upload_time.day)
        )
        # If there is no such path, create
        if not os.path.exists(path):
            os.makedirs(path)

        file_path = os.path.join(path, file_obj.name)

        file_url = f'{settings.MEDIA_URL}tinymce/{upload_time.year}/{upload_time.month}/{upload_time.day}/{file_obj.name}'

        if os.path.exists(file_path):
            return JsonResponse({
                "message": "file already exist",
                'location': file_url
            })

        with open(file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)

        return JsonResponse({
            'message': 'Image uploaded successfully',
            'location': file_url
        })
    return JsonResponse({'detail': "Wrong request"})


class GetPDFProtocol(APIView):
    """Получение сформированного протокола из локальной файловой
    системы"""
    def get(self, request, event_id):
        protocol_name = f'protocol_event_{event_id}.pdf'
        path = f'/home/atlima/atlima_django_backend/atlima_backend_core/atlima_backend_structure/protocols/{protocol_name}'
        try:
            protocol = open(path, 'rb')
        except FileNotFoundError:
            protocol = None
        if protocol:
            return FileResponse(open(path, 'rb'))
        else:
            return JsonResponse({"status": False, "errors": {"event_id": ["no protocol for event"]}}, status=404)


def get_email_template_content(language, template):
    try:
        content = EmailTemplate.objects.get(related_template=template, language=language)
    except ObjectDoesNotExist:
        content = None
    return content


def get_template_content(content, params):

    template_content = content
    

    mapping = {}
    variables = template_content.split(' ')
    default_variables = [template_variable for template_variable in variables if template_variable[0] == "$"]
    for nlvariables in variables:
        vars = nlvariables.split('\n')
        if len(nlvariables) > 1:
            for v in vars:
                if v[0] == '$':
                    default_variables.append(v)

    for template_variable in default_variables:
        json_attribute = (template_variable[1:].strip()).replace(',', '').replace('.', '').replace('!', '').replace(';', '')
        template_variable_for_mapping = template_variable.replace(',', '').replace('.', '').replace('!', '').replace(';',
                                                                                                                 '')
        try:
            mapping[template_variable_for_mapping] = params[json_attribute]
        except KeyError:
            mapping[template_variable_for_mapping] = ''
    
    for k, v in mapping.items():
        if v:
            template_content = template_content.replace(k, v)
        else:
            template_content = template_content.replace(k, '')

    return template_content

