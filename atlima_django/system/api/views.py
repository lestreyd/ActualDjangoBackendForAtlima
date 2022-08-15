from json import JSONDecodeError
from atlima_django.system.models import UserAgreement
from django.http import JsonResponse
from rest_framework.views import APIView
from atlima_django.system.api.serializers import SystemTypeSerializer
from rest_framework import generics
from atlima_django.system.models import SystemObject

# получение пользовательского соглашения
class GetLegal(APIView):
    def get(self, request):
        user_agreement = UserAgreement.objects.order_by(
            '-document_version'
        ).first()

        if user_agreement:
            user_agreement_data = {'title': user_agreement.title,
                                'content': user_agreement.content,
                                'document_version': user_agreement.document_version}
            return JsonResponse(user_agreement_data)
        return JsonResponse(None)
    
    
class AtlimaSysTypes(generics.ListAPIView):
    serializer_class = SystemTypeSerializer
    queryset = SystemObject.objects.all()
    
