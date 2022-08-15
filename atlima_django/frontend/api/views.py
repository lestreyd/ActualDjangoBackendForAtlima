from rest_framework.views import APIView
from ..models import FrontendTranslation, FrontendLog
import json
from django.http import HttpResponse, JsonResponse


# получение языковых пакетов для фронтенда
class AvailableLanguagePackages(APIView):
    def get(self, request):

        translations = FrontendTranslation.objects.all()
        available_translations = []
        for translation in translations:
            sample = {}
            sample['id'] = translation.id
            sample['langCode'] = translation.lang_code
            available_translations.append(sample)
        result = json.dumps(available_translations)
        return HttpResponse(result, content_type="application/json")
    

# выдача контента по требованию
class LanguagePackagesContent(APIView):
    def get(self, request):
        translations = FrontendTranslation.objects.all()
        translations = []
        for translation in translations:
            sample = {}
            sample['id'] = translation.id
            sample['langCode'] = translation.lang_code
            sample['data'] = translation.data
            translations.append(sample)

        j = json.dumps(translation)
        return HttpResponse(j, content_type="application/json")
    
    
# выдача контента на языке
class SpecificLanguageContent(APIView):
    """
        POST method for get Translation object with specific langCode or langId.
        Returns JSON from Translation instance "content" field.
    """

    def post(self, request):
        received_json_data = request.data

        lang_code = received_json_data.get('langCode')
        lang_id = received_json_data.get('langId')

        lang_package = None

        if lang_code:
            lang_package = FrontendTranslation.objects.filter(
                lang_code=lang_code).last()

        if lang_id:
            lang_package = FrontendTranslation.objects.filter(id=lang_id).last()

        if lang_package:
            lang_package_data = lang_package.data
            lang_package_data = json.dumps(lang_package_data)

        else:
            return JsonResponse(
            {"status": False,
                "errors": {
                    "language_package": ["Not found"]
                }
            }, status=404)

        return HttpResponse(lang_package_data, content_type="application/json")
    
    
# очистить лог фронта
class FrontendLogCleaner(APIView):

    def delete(self, request):
        if request.version == "1.0" or request.version is None:
            logs = FrontendLog.objects.all()
            logs.delete()
        else:
            logs = FrontendLog.objects.all()
            logs.delete()


