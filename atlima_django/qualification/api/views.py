from models import OfficialQualification
from serializers import OfficialQualificationSerializer
from django.http import JsonResponse
from rest_framework.views import APIView
from atlima_django.sport.models import Sport
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated


class OfficialQualificationView(APIView):
    """Официальная квалификация пользователя:
    - инструкторская
    - судейская
    - спортивная"""

    authentication_classes = [
        BasicAuthentication,
        TokenAuthentication,
    ]
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        user = request.user
        user_qualifications = OfficialQualification.objects.filter(user=user, approved=True)
        serializer = OfficialQualificationSerializer
        serialized = serializer(user_qualifications, many=True)
        return JsonResponse(serialized.data, safe=False)


    def post(self, request):

        """Создать профиль квалификации"""
        user = request.user
        data = request.data

        try:
            sport_type = data["sport_type"]
            sport_type_object = Sport.objects.get(id=sport_type)
        except KeyError:
            return JsonResponse(
                {"status": False, "message": "Field sport_type is required"}, status=400
            )

        try:
            qualification = data["qualification"]
        except KeyError:
            return JsonResponse(
                {"status": False, "message": "Field qualification is required"},
                status=400,
            )
        try:
            category = data["category"]
        except KeyError:
            return JsonResponse(
                {"status": False, "message": "Field category is required"}, status=400
            )

        iroa = data.get("IROA")
        
        approved_date = data.get('approved_date')

        if iroa is None:
            qualification_object = OfficialQualification.objects.create(
                user=user,
                sport_type=sport_type_object,
                qualification=qualification,
                category=category,
                IROA=False,
                approved_date = approved_date
            )
        else:
            qualification_object = OfficialQualification.objects.create(
                user=user,
                sport_type=sport_type_object,
                qualification=qualification,
                category=category,
                IROA=iroa,
                approved_date = approved_date
            )

        qualification_object.save()
        return JsonResponse({"status": True, "id": qualification_object.id})


    def put(self, request, qualification_id):
        """Подтвердить квалификацию пользователя"""
        try:
            qualification = OfficialQualification.objects.get(id=qualification_id)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": False, "message": "Qualification does not exists"},
                status=404
            )

        qualification.approved = True
        qualification.save()
        return JsonResponse({"status": True})

            
    def delete(self, request, qualification_id):
        data = request.data
        dismiss_reason = data.get('dismiss_reason')

        try:
            qualification = OfficialQualification.objects.get(id=qualification_id)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": False, "errors": {"qualification" :["does not exists"]}},
                status=404
            )

        qualification.approved = False
        qualification.dismiss_reason = dismiss_reason
        qualification.save()
        return JsonResponse({"status": True})


class QualificationDocumentUpload(APIView):
    authentication_classes = [
        BasicAuthentication,
        TokenAuthentication,
    ]
    permission_classes = [IsAuthenticated]

    def post(self, request, qualification_profile_id):
        try:
            data = request.data["document"]
            try:
                instance = OfficialQualification.objects.get(
                    id=qualification_profile_id
                )

                instance.document_file = data
                instance.save()
                return JsonResponse({"status": True})
            except ObjectDoesNotExist:
                return JsonResponse(
                    {"status": False, "message": "Official Qualification not found"},
                    status=404
                )
        except KeyError:
            return JsonResponse({"status": False, "message": "No document attached"}, status=400)



# УПРАВЛЕНИЕ ОФИЦИАЛЬНОЙ КВАЛИФИКАЦИЕЙ

class OfficialQualificationAllView(APIView):
    """все квалификации"""

    authentication_classes = [
        TokenAuthentication,
    ]
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        user = request.user
        user_qualifications = OfficialQualification.objects.filter(user=user)
        serializer = OfficialQualificationSerializer
        serialized = serializer(user_qualifications, many=True)
        return JsonResponse(serialized.data, safe=False)