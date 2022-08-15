from rest_framework import generics
from atlima_django.sport.models import Sport
from serializers import SportTypeSerializerv3
from rest_framework.authentication import TokenAuthentication
from django.db import transaction
from atlima_django.sport.models import SportAdministrator, Sport
from rest_framework.views import APIView
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from atlima_django.sport.api.serializers import (SportAdministratorSerializer2, 
                                                 SportAdministratorSerializer)

class SportList(generics.ListAPIView):
    # список всех эккземпляров спорта в системе
    authentication_classes = [TokenAuthentication]
    queryset = Sport.objects.all()
    serializer_class = SportTypeSerializerv3




# подсистема администрирования видов спорта 
class SportAdministratorManagement(APIView):

    authentication_classes = [TokenAuthentication]

    @transaction.atomic
    def post(self, request, sport_id):
        """Добавить пользователя в администраторы вида спорта"""
        user = request.user
        try:
            sport = Sport.objects.get(id=sport_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"sport_id": ["sport not found"]}}, status=404)

        is_admin = SportAdministrator.objects.filter(user=user, sport=sport).first()
        if not is_admin:
            return JsonResponse({"status": False, "errors": {"not_admin": ["you are not sport admin"]}}, status=403)
        data = request.data
        photo = data['photo']
        if photo is None:
            return JsonResponse({"status": False, "errors": {"photo": ["is required"]}}, status=400)
        sport.photo = photo
        sport.save()

        return JsonResponse({"status": True})

    
    @transaction.atomic
    def put(self, request, sport_id):

        user = request.user
        
        try:
            sport = Sport.objects.get(id=sport_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"sport_id": ["sport not found"]}}, status=404)

        is_admin = SportAdministrator.objects.filter(user=user, sport=sport).first()
        if not is_admin:
            return JsonResponse({"status": False, "errors": {"not_admin": ["you are not sport admin"]}}, status=403)

        data = request.data

        errors = {}
        
        slug = data.get('slug')
        descriptions = data.get('descriptions')
        site = data.get('site')
        events_is_moderated = data.get('events_is_moderated')

        if slug:
            check_slug = Sport.objects.filter(Q(slug=slug)&~Q(id=sport_id)).first()
            if check_slug:
                errors['slug'] = ['not unique']
        
        if len(errors) > 0:
            return JsonResponse({"status": False, "errors": errors}, status=400)
        
        if site:
            sport.site = site
        if slug:
            sport.slug = slug
        if descriptions:
            for item in descriptions:
                
                try:
                    language_id = item['language_id']
                    title = item['title']
                    description = item['description']
                    sport_content = Sport.objects.filter(id=sport_id).first()

                    if not sport_content:
                        new_sport_content = Sport.objects.create(sport_content=sport, 
                                                                 title=title, 
                                                                 description=description)
                        new_sport_content.save()
                    else:
                        sport_content.title = title
                        sport_content.description = description
                        sport_content.save()
                        
                except KeyError or ObjectDoesNotExist:
                    continue

        if events_is_moderated is not None:
            sport.events_is_moderated = events_is_moderated
            sport.save()
        
        sport.save()
        return JsonResponse({"status": True})
    
    
# роут создания нового вида спорта (не используется фронтом)
class NewSport(APIView):

    authentication_classes = [TokenAuthentication]

    @transaction.atomic
    def post(self, request):

        user = request.user
        
        is_country_admin = SportAdministrator.objects.filter(user=user, region__isnull=True).first()
        if not is_country_admin:
            return JsonResponse({"status": False, "errors": {"sport_admin": ['only']}}, status=403)
        data = request.data

        errors = {}
        site = None
        slug = None
        descriptions = None
        events_is_moderated = None

        try:
            slug = data['slug']
            descriptions = data['descriptions']
            site = data['site']
            events_is_moderated = data['events_is_moderated']
        except KeyError as ke:
            pass

        if not slug:
            errors['slug_field'] = ['slug is required']

        if slug or slug == "":
            check_slug = Sport.objects.filter(slug=slug).first()
            if check_slug:
                errors['slug_unique'] = ['not unique']
        
        if not site:
            errors['site'] = ['is required']
        
        if events_is_moderated is None:
            errors['events_is_moderated'] = ['is required']

        if descriptions is None:
            errors['descriptions'] = ['is required']
        else:
            for desc in descriptions:
                try:
                    language_id = desc['language_id']
                    title = desc['title']
                    description = desc['description']
                except KeyError as ke:
                    error = str(ke)
                    errors[error] = ['wrong descriptions structure']
                    break
                except ObjectDoesNotExist:
                    errors['language'] = ['not found']
                    break

        if len(errors) > 0:
            return JsonResponse({"status": False, "errors": errors}, status=400)
        else:
            new_sport = Sport.objects.create(site = site, slug = slug, owner=user)
            new_sport.save()

            for title_and_desc in descriptions:
                language_id = title_and_desc['language_id']
                title = title_and_desc['title']
                description = title_and_desc['description']
                new_content_sport = Sport.objects.create(title = title,
                                                        description = description)
                new_content_sport.save()
        
        return JsonResponse({"status": True})
    
    
class SportAdministrators(APIView):
    """Администраторы вида спорта"""
    def get(self, request, sport_id):
        serializer = SportAdministratorSerializer2
        try:
            sport = Sport.objects.get(id=sport_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {'sport_id': ["not found"]}})
        sport_admins = SportAdministrator.objects.filter(sport=sport).all()
        serialized = serializer(sport_admins, many=True, context={'request': request})
        return JsonResponse(serialized.data, safe=False)


class AdminScreenV2(generics.ListAPIView):
    serializer_class = SportAdministratorSerializer
    queryset = SportAdministrator.objects.all()


