from atlima_django.sport_events.models import (Event, 
                                               EventFormat, 
                                               EventProperty,
                                               EventEVSKStatus)
from atlima_django.sport_events.api.utils import get_event_participants
from django.views import APIView
from rest_framework.authentication import (SessionAuthentication, 
                                           BasicAuthentication, 
                                           TokenAuthentication)
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.ipsc.api.serializers import DisciplineSerializer
from django.http import JsonResponse
from django.db import transaction
from atlima_django.sport_events.api.utils import get_event_participants
from atlima_django.location.models import City
from atlima_django.sport.models import Sport
from api.utils import get_event_participants
from atlima_django.common.models import Organizer
from atlima_django.money.models import PriceConfiguration, Currency, OrderItem
from django.conf import settings
from atlima_django.ipsc.models import Discipline
from atlima_django.common.api.utils import create_system_event_object
from constance import config
from atlima_django.ipsc.api.utils import recreate_squads_by_event
from atlima_django.referee.models import RefereeSlot
from atlima_django.sport_events.api.serializers import EventMenuSerializer, EventModelSerializer
from atlima_django.common.models import OrganizerAdministration
from atlima_django.sport_events.models import Slot
from atlima_django.ipsc.models import Team, Division, Discipline, Squad
from atlima_django.money.models import PromoCode, TransactionHistory, Order
from rest_framework.views import generics
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from django.db.models import CharField
from atlima_django.sport_events.models import EventRefereeInvite, EventAdministration, EventShortSerializer
from atlima_django.users.models import User
import random
from datetime import date
from models import EventProperty, UserInterestedIn
from atlima_django.referee.models import EventRefereeInvite, EventOffer
from atlima_django.users.api.serializers import UserSerializer
from atlima_django.posts.models import Post, PostAttachment
from atlima_django.money.api.serializers import PromocodeSerializer
import string
import json
from atlima_django.sport_events.api.serializers import SlotSerializer
from atlima_django.sport_events.api.serializers import EVSKStatusSerializer
from django.db.models.functions import Lower
from atlima_django.money.models import PromoCode
from atlima_django.money.api.merchant import TinkoffMerchantAPI
from atlima_django.money.api.views import TINKOFF_TERMINAL_KEY, TINKOFF_PASSWORD



class EventMainMenu(APIView):
    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        events = Event.objects.filter(Q(status=Event.PUBLISH)
                                      &Q(approved=True))
        event_list = []
        for event in events:
            event_parameters = {}
            event_parameters['id'] = event.id
            event_title = event.title
            event_description = event.description
            event_parameters['title'] = event_title
            event_parameters['description'] = event_description

            sport = event.sport.title
            event_parameters['sport_type'] = {
                "id": event.sport.id,
                "title": sport.title
            }
            
            if sport_title.count()>0:
                sport_title=sport_title.first()
                event_parameters['sport_type'] = {'id': sport_title.sport_content.id, 
                                                  'title': sport_title.title}
            else:
                event_parameters['sport_type'] = None

            ###

            # 3 Фото
            if event.photo:
                event_parameters['photo'] = event.photo.event_photo.url

            # 4 Статус
            event_parameters['status'] = event.status
            
            # 5 Адресная информация
            language = self.get_language(request=request)
            if language.code == 'ru':
                if event.country:
                    event_parameters['country'] = {'id': event.country.id, 
                                                   'title': event.country.short_name}
                if event.region:
                    event_parameters['region'] = {'id': event.region.id, 
                                                  'title': event.region.title}
                if event.city:
                    event_parameters['city'] = {'id': event.city.id, 
                                                'title': event.city.settlement}
            else:
                if event.country:
                    event_parameters['country'] = {'id': event.country.id, 
                                                   'title': event.country.english_name}
                if event.region:
                    event_parameters['region'] = {'id': event.region.id, 
                                                  'title': event.region.english_name}
                if event.city:
                    event_parameters['city'] = {'id': event.city.id, 
                                                'title': event.city.english_name}

            event_parameters['location'] = event.location
            event_parameters['site'] = event.site

            # slug
            event_parameters['slug'] = event.slug

            # даты
            event_parameters['start_event_date'] = event.start_event_date
            event_parameters['end_event_date'] = event.end_event_date

            # формат
            if event.format:
                format_content = EventFormat.objects.get(format=event.format)
                if format_content:
                    event_parameters['format'] = format_content.title
            
            event_parameters['approved'] = event.approved

            # 3 проверяем на динамические свойства
            try:
                practical_shooting_properties = EventProperty.objects.get(event=event)
            except ObjectDoesNotExist:
                practical_shooting_properties = None


            if practical_shooting_properties:


                event_parameters['properties'] = {}
                # weapon = WeaponTypeLanguageSpecific.objects.get(weapon=practical_shooting_properties.weapon, language=language)
                serializer = DisciplineSerializer
                if event.disciplines is not None:
                    event_disciplines = serializer(event.disciplines, many=True)
                    disciplines = event_disciplines.data
                    event_parameters['disciplines'] = disciplines
                else:
                    event_parameters['disciplines'] = []
                event_parameters['properties']['id'] = practical_shooting_properties.id
                event_parameters['properties']['match_level'] = practical_shooting_properties.match_level
                event_parameters['properties']['exercices_amount'] = practical_shooting_properties.exercices_amount
                event_parameters['properties']['min_shoots_amount'] = practical_shooting_properties.min_shoots_amount
                event_parameters['properties']['squads_amount'] = practical_shooting_properties.squads_amount
                event_parameters['properties']['shooters_in_squad'] = practical_shooting_properties.shooters_in_squad
                event_parameters['properties']['prematch'] = practical_shooting_properties.prematch
                participants = get_event_participants(event)
                if participants:
                    event_parameters['participants'] = participants
                else:
                    event_parameters['participants'] = []

            event_list.append(event_parameters)

        result = {}
        result['events'] = event_list
        return JsonResponse(result, safe=False, status=200)
  
    
    
class EventCreation(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    @transaction.atomic
    def post(self, request, event_id):
        if request.version == "1.0" or request.version is None:
            data = request.data
            
            # Заголовок, содержит основную информацию о мероприятии
            # screen - event-edit-1
            event_draft = Event.objects.get(id=event_id)

            sport_type = data.get('sport_id')
            format = data.get('format_id')
            start_event_datetime = data.get('start_event_datetime')
            end_event_datetime = data.get('end_event_datetime')
            site = data.get('site')
            slug = data.get('slug')
            city = data.get('city_id')
            location = data.get('location')
            organizer = data.get('organizer_id')
            evsk = data.get('evsk')

            # multilanguage descriptions
            descriptions = data.get('descriptions')
            standart_speed_courses = data.get('standart_speed_courses')
            phone = data.get('phone')
            email = data.get('email')
            properties = data.get('properties')
            event_draft.phone = phone
            event_draft.email = email
            
            # create event from provided information (Header)

            # Проверяем все объекты для обязательных полей
            # Спорт
            if sport_type:
                try:
                    sport_instance = Sport.objects.get(id=sport_type)
                    event_draft.sport_type = sport_instance
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, 
                                         "message": "Incorrect sport type"}, 
                                        status=400)
            
            if format:
                # Формат
                try:
                    format_instance = EventFormat.objects.get(id=format)
                    event_draft.format = format_instance
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, 
                                         "message": "Incorrect format"}, 
                                        status=400)
            
            if city:
                # Город
                try:
                    city_instance = City.objects.get(id=city)
                    region_instance = city_instance.region
                    country_instance = region_instance.country
                    
                    event_draft.city = city_instance
                    event_draft.region = region_instance
                    event_draft.country = country_instance

                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "message": "No city with provided id"}, status=400)
            
            if organizer:
                # Организатор
                try:
                    organizer_instance = Organizer.objects.get(id=organizer)
                    event_draft.organizer = organizer_instance
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "message": "No organizer with provided id"}, status=400)

            # обновление полей черновика мероприятия
            if location:
                event_draft.location = location
            if start_event_datetime:
                event_draft.start_event_date = start_event_datetime
            if end_event_datetime:
                event_draft.end_event_date = end_event_datetime
            if slug:
                event_draft.slug = slug
            if site:
                event_draft.site = site

            if event_draft.banned is not None:
                event_draft.banned_moderation = True

            if evsk is not None:
                evsk_instance = EventEVSKStatus.objects.get(id=evsk)
                if event_draft.moderated is True or event_draft.approved is True:
                    if event_draft.evsk is not None:
                        if event_draft.evsk.regional_status is None and evsk_instance.regional_status is not None:
                            event_draft.evsk = evsk_instance
                            event_draft.approved = False
                            event_draft.moderated = True
                            event_draft.status = Event.DRAFT
                        elif event_draft.evsk.regional_status is not None and evsk_instance.regional_status is None:
                            event_draft.evsk = evsk_instance
                            event_draft.approved = True
                            event_draft.moderated = False
                    else:
                        event_draft.evsk = evsk_instance
                        if evsk_instance.regional_status is None:
                            event_draft.moderated = False
                            event_draft.approved = True
                        else:
                            event_draft.moderated = True
                            event_draft.approved = False
                        event_draft.save()
                else:
                    event_draft.evsk = evsk_instance
                    if evsk_instance.regional_status is None:
                        event_draft.moderated = False
                        event_draft.approved = True
                    else:
                        event_draft.moderated = True
                        event_draft.approved = False
                    event_draft.save()

            if descriptions:
                
                for description in descriptions:
                    language = description['language_id']
                    title = description['title']
                    description = description['description']
                    
                    languages = settings.LANGUAGES
                    
                    for i, language_content in (enumerate(languages)):
                        if i - 1 == language:
                            code = language_content[0]
                            event_draft.set_current_language(code)
                            event_draft.title = title
                            event_draft.description = description
            event_draft.save()
            # add photo - use route below (AddEventPhoto)

            # screen - event-edit-2
            # фактические свойства - свойства, установленные на событии
            fact_properties, _ = EventProperty.objects.get_or_create(event=event_draft)

            # получаем все свойства из того, что прислало приложение
            # добавляем новые свойства и пересчитываем скводы со стрелками
            # по параметрам, заданным в конфигурации системы
            disciplines = properties.get('disciplines')
            match_level = properties.get('match_level')
            exercise_amount = properties.get('exercices_amount')
            min_shot_count = properties.get('min_shoots_amount')
            squads_amount = properties.get('squads_amount')
            prematch = properties.get('prematch')
            number_in_calendar_plan = properties.get('number_in_calendar_plan')
            shooters_in_squad = properties.get('shooters_in_squad')

            if disciplines:
                fact_properties.disciplines.clear()
                discipline_instances = Discipline.objects.filter(id__in=disciplines).all()
                for discipline in discipline_instances:
                    fact_properties.disciplines.add(discipline)
            if match_level is not None:
                fact_properties.match_level = match_level
            if exercise_amount is not None:
                fact_properties.exercise_amount = exercise_amount
            if min_shot_count is not None:
                fact_properties.min_shoots_amount = min_shot_count
            if squads_amount is not None:
                fact_properties.squad_amount = squads_amount
            if shooters_in_squad is not None:
                fact_properties.shooters_in_squad = shooters_in_squad
            if prematch is not None:
                fact_properties.prematch = prematch
            if number_in_calendar_plan is not None:
                fact_properties.number_in_calendar_plan = number_in_calendar_plan
            fact_properties.save()

            if fact_properties.squads_amount == 0:
                fact_properties.squads_amount = config.IPSC_DEFAULT_SQUADS_AMOUNT
            if fact_properties.min_shoots_amount == 0:
                fact_properties.min_shoots_amount = config.IPSC_DEFAULT_SHOOTERS_AMOUNT
            # выставили всё по умолчанию из конфигурации и сохраняем
            fact_properties.save()

            registration_opened = data.get('registration_opened')
            price_option = data.get('price_option')
            price = data.get('price')
            currency = data.get('currency_id')
            shot_price = data.get('shot_price')
            shot_price_currency = data.get('shot_price_currency_id')

            if currency:
                try:
                    event_price_currency_instance = Currency.objects.get(id=currency)
                    event_draft.currency = event_price_currency_instance
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "message": "No currency with provided id (price)"}, status=400)

            if shot_price_currency:
                try:
                    shot_price_currency_instance = Currency.objects.get(id=shot_price_currency)
                    event_draft.shot_price_currency = shot_price_currency_instance
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "message": "No currency with provided id (shot_price)"}, status=400)

            if price_option:
                try:
                    price_option_instance = PriceConfiguration.objects.get(id=price_option)
                    event_draft.price_option = price_option_instance
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "message": "No price option with provided id"}, status=400)

            if price:
                event_draft.price = price
            if shot_price:
                event_draft.shot_price = shot_price
            if standart_speed_courses is not None:
                event_draft.standart_speed_courses = standart_speed_courses
            if registration_opened is not None:
                event_draft.registration_opened = registration_opened
            event_draft.save()
            # вносим изменения в пользователя - добавляем системное событие
            try:
                create_system_event_object(request.user, 'event_changed', {'id': event_draft.id})
            except:
                pass

            return JsonResponse({"status": True, "id": event_draft.id})
        
        
        
class AddEventPhoto(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, event_id):
        data = request.data['photo']
        try:
            event = Event.objects.get(id=event_id)
            if data is not None:
                event.photo = data
                event.save()
        except ObjectDoesNotExist:
                return JsonResponse({"status": False, 
                                    "errors": {
                                        "event": ["not found"]
                                    }}, status=404)
        except KeyError as error:
            return JsonResponse({"status": False, "message": "Failed, error: no parameters (form-data photo)"}, status=400)
        except Exception as e:
            return JsonResponse({"status": False, "message": f"Error during loading to server: {e}"}, safe=False, status=400)
        return JsonResponse({"status": True})
    
    
class Formats(APIView):
    
    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        formats = EventFormat.objects.all()
        event_format_list = []
        for event_format in formats:
            event_format_sample = {}
            event_format_sample['id'] = event_format.format.id
            event_format_sample['title'] = event_format.title
            event_format_sample['description'] = event_format.description
            event_format_list.append(event_format_sample)
        result = {}
        result['formats'] = event_format_list

        return JsonResponse(result, safe=False, status=200)


# ЗДЕСЬ происходит публикация события. После публикации
# становится доступной функциональность размещения участников
# по слотам, подсчёт результатов и фиксация рейтинга.
class PublishEvent(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def put(self, request, event_id):
        data = request.data
        user = request.user

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors":{'event_id': ['not found']}}, status=404)
        
        director = event.director
        if director is None:
            return JsonResponse({"status": False, "errors": {"director": ["must be assigned!"]}}, status=400)

        manual_publication = data.get('publish')

        manual_publication = manual_publication if manual_publication is not None else True

        

        if event.status == Event.DRAFT and manual_publication is True:
            event.status = Event.PUBLISH

            practical_shooting_property = EventProperty.objects.get(event=event)
            count_disciplines = practical_shooting_property.disciplines.count()
            if count_disciplines < 1:
                return JsonResponse({"status": False, "errors": {"disciplines": {['no disciplines found']}}}, status=400)
            squads_amount = practical_shooting_property.squads_amount
            recreate_squads_by_event(event=event, squads_amount=squads_amount)
            sport = event.sport_type

            if event.evsk.regional_status is not None:
                event.moderated = True
                event.approved = False

            if event.banned is not None:
                event.banned_moderation = True
            
            if sport.events_is_moderated is False:
                event.approved = True
                event.moderated = False
            else:
                if event.evsk.regional_status is not None:
                    event.approved = False
                    event.moderated = True
                else:
                    event.approved = True
                    event.moderated = False

            event.save()
        else:
            pass
            
        return JsonResponse({"status": True})


class BanEvent(APIView):
    """Передать событие в бан"""
    def put(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except:
            return JsonResponse({"status": False, "errors": {'event': ['not found']}}, status=404)
        event.banned = True
        event.save()
        return JsonResponse({"status": True})


class UnbanEvent(APIView):
    """Вывести событие из бана(проставить флаг !bannned)"""
    def put(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except:
            return JsonResponse({"status": False, "errors": {'event': ['not found']}}, status=404)
        event.banned = None
        event.banned_moderation = False
        event.save()
        return JsonResponse({"status": True})



class EventListv2(generics.ListAPIView):
    """Новый список событий с учётом пагинации
    и фильтров для поиска"""
    pagination_class = LimitOffsetPagination
    serializer_class = EventMenuSerializer

    def get_queryset(self):
        request = self.request
        if request.version == "1.0" or request.version is None:
            search_term = request.GET.get('search_term', None)
            past_events = request.GET.get('past', None)
            future_events = request.GET.get('future', None)

            date_from = request.GET.get('date_from', None)
            date_to = request.GET.get('date_to', None)

            weapon = request.GET.get('weapon', None)
            only_mine = request.GET.get('only_mine', None)

            organizers = request.GET.getlist('organizers[]')
            sports = request.GET.getlist('sports[]')
            divisions = request.GET.getlist('divisions[]')
            match_levels = request.GET.getlist('match_levels[]')
            regions = request.GET.getlist('regions[]')

            if search_term == "": search_term = None
            if past_events == "": past_events = None
            if future_events == "": future_events = None
            if date_from == "": date_from = None
            if date_to == "": date_to = None
            if weapon == "": weapon = None
            if only_mine == "": only_mine = None
            if regions == []: regions = None

            if organizers == []: organizers = None
            if sports == []: sports = None
            if divisions == []: divisions = None
            if match_levels == []: match_levels = None

            if search_term is not None:
                CharField.register_lookup(Lower, "lower")
                search_term = search_term.lower()

                # 2. поиск по заголовкам и описаниям мероприятий
                result = Event.objects.filter(Q(titles__title=search_term)&Q(status='Publish')&Q(approved=True)&Q(banned__isnull=True)).all()
                
                if sports is not None:
                    result = result.filter(sport_type__id__in=sports)

                if organizers is not None:
                    result = result.filter(organizer__id__in=organizers)
                
                if regions is not None:
                    result = result.filter(region__id__in=regions)
                
                if divisions is not None:
                    disciplines = Discipline.objects.filter(division__in = divisions)
                    properties = EventProperty.objects.filter(disciplines__in=disciplines).values_list('event', flat=True)
                    result = result.filter(id__in=properties)

                if weapon is not None:
                    disciplines2 = Discipline.objects.filter(weapon__id=weapon)
                    properties2 = EventProperty.objects.filter(disciplines__in=disciplines2).values_list('event', flat=True)
                    result = result.filter(id__in=properties2)
                
                if only_mine is not None:
                    if type(request.user) == User:
                        
                        slots = Slot.objects.filter(user=request.user, paid=True, active=True).values_list('event', flat=True)
                        admins = EventAdministration.objects.filter(user=profile).values_list('event', flat=True)
                        referee = RefereeSlot.objects.filter(user=request.user).values_list('event', flat=True)
                        interested = UserInterestedIn.objects.filter(user=request.user).values_list('event', flat=True)
                        
                        invited = EventRefereeInvite.objects.filter(user=request.user, status=EventRefereeInvite.WAITING).values_list('event', flat=True)
                        
                        overall = slots.union(admins, referee, interested, invited)
                        overall_events = result.filter(id__in=overall).all()
                        result = overall_events.order_by('start_event_date')
                    else:
                        pass

                if date_from is not None:
                    result = result.filter(start_event_date__gte = date_from).order_by('start_event_date')

                if date_to is not None:
                    result = result.filter(Q(start_event_date__lte = date_to)|Q(end_event_date__isnull=True)|Q(end_event_date__lte=date_to)).order_by('start_event_date')
                
                if past_events is not None:
                    result = result.filter(Q(start_event_date__lte=date.today())&(Q(end_event_date__isnull=True)|Q(end_event_date__lte=date.today()))).order_by('-start_event_date')
                    # result = result.intersection(queryset_past)

                if future_events is not None:
                    result = result.filter(start_event_date__gte=date.today()).order_by('start_event_date')
            else:
                result = Event.objects.filter(approved=True, status=Event.PUBLISH, dismissed=False, moderated=False, banned__isnull=True).order_by('start_event_date')

                if sports is not None:
                    result = result.filter(sport_type__id__in=sports)
                
                if organizers is not None:
                    result = result.filter(organizer__id__in=organizers)

                if regions is not None:
                    result = result.filter(region__id__in=regions)
                
                if divisions is not None:
                    disciplines = Discipline.objects.filter(division__in = divisions)
                    properties = EventProperty.objects.filter(disciplines__in=disciplines).values_list('event', flat=True)
                    result = result.filter(id__in=properties)

                if only_mine is not None:
                    if type(request.user) == User:

                        profile = request.user
                        
                        slots = Slot.objects.filter(user=request.user, paid=True, active=True).values_list('event', flat=True)
                        admins = EventAdministration.objects.filter(user=profile).values_list('event', flat=True)
                        referee = RefereeSlot.objects.filter(user=request.user).values_list('event', flat=True)
                        interested = UserInterestedIn.objects.filter(user=request.user).values_list('event', flat=True)
                        
                        invited = EventRefereeInvite.objects.filter(user=request.user, status=EventRefereeInvite.WAITING).values_list('event', flat=True)
                        
                        overall = slots.union(admins, referee, interested, invited)
                        overall_events = result.filter(id__in=overall).all()
                        result = overall_events.order_by('start_event_date')
                    else:
                        pass

                if date_from is not None:
                    result = result.filter(start_event_date__gte = date_from).order_by('start_event_date')

                if date_to is not None:
                    result = result.filter(start_event_date__lte = date_to).order_by('start_event_date')

                if past_events is not None:
                    result = result.filter(Q(start_event_date__lte=date.today())&(Q(end_event_date__isnull=True)|Q(end_event_date__lte=date.today()))).order_by('-start_event_date')
                    # result = result.intersection(queryset_past)

                if future_events is not None:
                    result = result.filter(start_event_date__gte=date.today()).order_by('start_event_date')

            return result
        
        
        
class EventDeletion(APIView):
    """мягкое удаление события. На событии проставляется
    статус DELETED с проверкой  флагов события"""
    def put(self, obj, event_id):
        request = self.request
        errors = {}

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            errors['event'] = ['not found']
        
        if event.completed:
            errors['completed'] = ['event is completed']

        if event.has_results:
            errors['has_results'] = ['event has results']

        if event.registration_opened:
            errors['registration_opened'] = ['registration for event is opened']

        if event.status == Event.PUBLISH:
            errors['publish'] = ['event is publish and showed in event list for users']

        referees_in_event = RefereeSlot.objects.filter(event=event).all()
        counter = referees_in_event.count()

        if counter > 0:
            errors['referees'] = ['event has referees assigned to event']

        slots = Slot.objects.filter(event=event, active=True, paid=True).all()
        slots_count = slots.count()
        if slots_count > 0:
            errors['slots'] = ['event has paid active slots']

        if len(errors) > 0:
            return JsonResponse({"status": False, "errors": errors}, status = 400)
        else:
            event.status = Event.DELETED
            event.save()
        
        return JsonResponse({"status": True})
    
    
class RemoveSlots(APIView):
    """Удаление слотов из системы"""
    def delete(self, request):
        slots = Slot.objects.all()
        slots.delete()
        return JsonResponse({"status": True})


# ВОЗВРАТ СЛОТА
class ReturnSlot(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, slot_id):
        # если слот пользователя, то зачищаем параметры
        user = request.user
        slot = Slot.objects.get(id=slot_id)

        slot_user = slot.user

        if user == slot_user:

            order = OrderItem.objects.filter(object_id=slot_id,
                                            object_type='Slot').last()
            
            if order:
                order_id = order.order_id
                
                payment_record = TransactionHistory.objects.filter(order_id=order_id.id, 
                                                                    operation="finish_authorize",
                                                                    success=True).last()
                # response = payment_record.response                    

                payment_id = payment_record.payment_id

                merchant = TinkoffMerchantAPI(terminal_key=TINKOFF_TERMINAL_KEY,
                                            secret_key=TINKOFF_PASSWORD)

                response = merchant.cancel(PaymentId=str(payment_id))
                answer = response.json()

                order_id = answer.get('OrderId')
                success = answer.get('Success')
                status = answer.get('Status')
                payment_id = answer.get('PaymentId')
                error_code = answer.get('ErrorCode')
                message = answer.get('Message')
                details = answer.get('Details')
                original_amount = answer.get('OriginalAmount')
                new_amount = answer.get('NewAmount')

                try:
                    bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.CANCEL,
                                                                    information_type=TransactionHistory.BANK_RESPONSE,
                                                                    order_id = order_id,
                                                                    success = success,
                                                                    status = status,
                                                                    payment_id = payment_id,
                                                                    error_code = error_code,
                                                                    message = message,
                                                                    details = details,
                                                                    response = answer)
                    bankresponse.save()
                except Exception:
                    pass
                
                if success is True:
                    slot.user = None
                    slot.paid = False
                    slot.save()

                    return JsonResponse({"status": True})
                else:
                    if message is not None:
                        return JsonResponse({"status": False, 'errors': {'message': [f"{message}"]}})
                    else:
                        return JsonResponse({"status": False})
            
            else:
                slot.user = None
                slot.paid = False
                slot.active = False
                slot.save()
                return JsonResponse({"status": True, "message": "This slot returned without cashback"})
        else:
            # если пользователь не совпадает с текущим пользователем, отказываем
            return JsonResponse({"status": False, "message": "This slot is applied for another user!"}, status=401)
        
        
        

class PostCreation(APIView):

    authentication_classes = [TokenAuthentication]

    def post(self, request):
        user = request.user
        data = request.data

        # фото и документы
        photos = request.FILES.getlist('photos')
        documents = request.FILES.getlist('documents')

        # для прикрепления события
        event_id = data.get('event_id')
        organizer_id = data.get('organizer_id')
        content = data['content']

        if organizer_id is not None:
            try:
                organizer = Organizer.objects.get(id=organizer_id)
                # создание нового поста
                new_post = Post.objects.create(creator_organizer=organizer,
                                            creator_user=user,
                                            content=content)
                new_post.save()
            except ObjectDoesNotExist:
                return JsonResponse({"status": False,
                                    "errors": {"organizer_id": ['not found']}},
                                    status=404)
        else:
            # создание нового поста
            new_post = Post.objects.create(creator_user=user,
                                        content=content)
            new_post.save()

        # создание аттачей
        for photo in photos:
            new_post_attach = PostAttachment.objects.create(photo=photo,
                                                            related_post=new_post)
            new_post_attach.save()

        for document in documents:
            new_post_attach = PostAttachment.objects.create(document=document,
                                                            related_post=new_post)

            new_post_attach.save()

        if event_id is not None:
            try:
                event = Event.objects.get(id=event_id)
                new_post_attach = PostAttachment.objects.create(event=event,
                                                                related_post=new_post)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"event_id": ["Not found"]}}, status=404)

        return JsonResponse({"status": True, "id": new_post.id})
     

class PostUpdate(APIView):

    def delete(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            post.active = False
            post.save()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False,
                                "errors": {"post_id": ['not found']}},
                                status=404)
        return JsonResponse({"status": True})


    def put(self, request, post_id):
        data = request.data
        user = request.user

        try:
            post = Post.objects.get(id=post_id)
            content = data.get('content')

            photos = data.get('photos')
            documents = data.get('documents')
            event_id = data.get('event_id')
            organizer_id = data.get('organizer_id')

            if content is not None:
                post.content = content
                post.save()

            if organizer_id is not None:
                try:
                    organizer = Organizer.objects.get(id=organizer_id)
                    # создание нового поста
                    post.creator_organizer = organizer
                    post.save()
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False,
                                        "errors": {"organizer_id": ['not found']}},
                                        status=404)
            # создание аттачей
            post_attachments = PostAttachment.objects.filter(related_post=post).all()
            post_attachments.delete()

            for photo in photos:
                new_post_attach = PostAttachment.objects.create(photo=photo,
                                                                related_post=post)
                new_post_attach.save()

            for document in documents:
                new_post_attach = PostAttachment.objects.create(document=document,
                                                                related_post=post)

                new_post_attach.save()

            if event_id is not None:
                try:
                    event = Event.objects.get(id=event_id)
                    new_post_attach = PostAttachment.objects.create(event=event,
                                                                    related_post=post)
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "errors": {"event_id": ["Not found"]}}, status=404)

        except ObjectDoesNotExist:
            return JsonResponse({"status": False,
                                "errors": {"post_id": ['not found']}},
                                status=404)

        return JsonResponse({"status": True})



# НОВЫЙ МЕХАНИЗМ СЛОТА С ПРОМОКОДОМ И ФОРМИРОВАНИЕМ ЗАКАЗА
class RegisterSlot(APIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def _get_event(self, event_id):
        event = Event.objects.filter(id=event_id).first()
        return event

    def _get_discipline(self, discipline_id):
        discipline = Discipline.objects.filter(id=discipline_id).first()
        return discipline

    def _get_promocode(self, promocode_id):
        promocode = PromoCode.objects.filter(id=promocode_id).first()
        return promocode

    def _create_team(self, event, discipline, team_title):
        new_team = Team.objects.create(title=team_title, event=event, discipline=discipline)
        new_team.save()
        return new_team

    def _check_team(self, event, team_title):
        team = Team.objects.filter(event=event, title=team_title).first()
        return team

    def _delete_interested(self, event, user):
        event_interested = UserInterestedIn.objects.filter(user=user, event=event).first()
        if event_interested:
            event_interested.delete()

    @transaction.atomic
    def post(self, request, event_id):
        data = request.data
        user = request.user

        errors = {}

        event = self._get_event(event_id)
        
        if event is None:
            errors['event'] = ['event is not found']
            return JsonResponse({"status": False, 'errors': errors}, status=404)

        # discipline_id = data.get('discipline_id')

        user_id = data.get('user_id')
        
        if user_id:
            user = User.objects.get(id=user_id)
        # else:
        #     return JsonResponse({"status": False, 'errors':{'user_id':['user cant be guest']}}, status=400)

        division = data.get('division')
        competition_type = data.get('competition_type')

        # discipline = self._get_discipline(discipline_id)
        discipline = Discipline.objects.filter(division__id=division,
                                                competition_type=competition_type).first()
        if discipline is None: errors['discipline'] = ['discipline is required']

        category = data.get('category')
        if category not in range(1, 7): errors['category'] = ['category must be 1-6 (SJ - SS)']

        power_factor = data.get('power_factor')
        if power_factor not in [1, 2]: errors['power_factor'] = ['power factor must be 1 or 2 (MIN - MAJ)']

        it_has_slot = Slot.objects.filter(event=event, user=user, paid=True, active=True).first()
        if it_has_slot is not None:
            return JsonResponse({"status": False, "errors": {"user": ["user already has slot"]}}, status=400)

        # вычисление цены 
        promocode_id = data.get('promocode_id')
        promocode = None
        if promocode_id is not None:
            promocode = self._get_promocode(promocode_id)
            if promocode:
                discount = promocode.discount
                price = int(event.price)
                final_price = price - (price * (discount / 100))
            else:
                final_price = event.price
        else:
            final_price = event.price

        paid = False

        if user_id:
            final_price = 0
            paid = True

        if event.price_option.id == 1:
            final_price = 0
            paid = True

        delegated_slot = Slot.objects.filter(promocode=promocode, 
                                            event=event, 
                                            user__isnull=True).first()
        if delegated_slot is not None:
            delegated_slot.user = user
            delegated_slot.active = True
            delegated_slot.paid = True
            delegated_slot.save()
            return JsonResponse({"status": True}, safe=False)

        if len(errors) > 0: return JsonResponse({"status": False, "errors": errors}, status=400)

        # создание слота
        participant_number = Slot.objects.all().count()
        new_slot = Slot.objects.create(user=user,
                                        event=event,
                                        discipline=discipline,
                                        category=category,
                                        power_factor=power_factor,
                                        final_price=final_price,
                                        participant_number=participant_number + 1,
                                        currency = event.currency,
                                        active=True,
                                        paid=paid)
        new_slot.save()
        self._delete_interested(new_slot.event, user)

        # добавление команды
        team_title = data.get('team_title')
        if team_title is not None:
            check = self._check_team(event, team_title)
            if check is None:
                new_team = Team.objects.create(title=team_title,
                                                discipline=discipline,
                                                event=event)
                new_team.save()
            else:
                teammates = Slot.objects.filter(team=check, event=event).count()
                if teammates < 4:
                    new_slot.team = check
                    new_slot.save()

        # новый заказ на слот
        if final_price > 0:
            new_order = Order.objects.create(amount=final_price * 100,
                                                status=False,
                                                user=user)
            new_order.save()

            # новая позиция в заказе
            new_order_item = OrderItem.objects.create(order_id=new_order,
                                                        object_type='Slot',
                                                        object_id=new_slot.id,
                                                        amount=final_price * 100,
                                                        promocode=promocode)
            new_order_item.save()
            new_order_id = new_order.id
        else:
            new_order_id = 0
            final_price = 0
            new_slot.paid = True
            new_slot.save()

        # создаём системное событие на регистрацию
        try:
            language = self.get_language(request=request)
            create_system_event_object(user, 'user_registered_on_event', {'user_id': user.id, 'id': event.id})
        except:
            pass

        return JsonResponse({"order_id": new_order_id, "amount": int(final_price * 100)})


class SingleEventInterface(APIView):
    # authentication_classes = [BasicAuthentication, TokenAuthentication]
    # permission_classes = [IsAuthenticated,]
    def get(self, request, event_id):
        serializer = EventModelSerializer
        errors = {}

        try:
            event = Event.objects.get(id=event_id)
            serialized = serializer(event, context={'request': request})
            data = serialized.data
            return JsonResponse(data)
        except ObjectDoesNotExist:
            errors['event_id'] = ['event not found']
        
        return JsonResponse({"status": False, "errors": errors})



class EventOfferView(APIView):

    def get(self, request, sender_type):
        if sender_type == 1:    
            # отправляем контент
            try:
                event_offer = EventOffer.objects.get(destination=EventOffer.FOR_USER)
            except:
                event_offer = None
        elif sender_type == 2:
            try:
                event_offer = EventOffer.objects.get(destination=EventOffer.FOR_ORGANIZER)
            except:
                event_offer = None

        if event_offer is not None:
            event_offer_content = EventOffer.objects.filter(oferta=event_offer).first()
            event_offer_response = {
                "id": event_offer_content.id,
                "content": event_offer_content.content
            }
        else:
            return JsonResponse({"status": False, "message": "Event offer is not founded"}, status=404)

        return JsonResponse(event_offer_response, safe=False)


class SetDirector(APIView):

    authentication_classes = [
        SessionAuthentication,
        BasicAuthentication,
        TokenAuthentication,
    ]
    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, event_id, user_id):
        post_data = request.data
        request_user = request.user

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event": ["not found"]}}, status=404)

        try:
            user = User.objects.get(id=user_id)
            # user = AtlimaUser.objects.get(user=user)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"user": ["not found"]}}, status=404)

        try:
            user_profile = request.user
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"profile": ["not found"]}}, status=404)

        try:
            admin_record = EventAdministration.objects.get(user=user_profile, event=event)
            is_director = admin_record.is_director
            
            if is_director:
                new_event_admin, _ = EventAdministration.objects.get_or_create(event=event, user=user_profile)
                new_event_admin.is_director = True
                new_event_admin.save()
                
                admin_record.is_director = False
                admin_record.save()
            else:
                return JsonResponse({"status": False, "errors": {"director": ["you are not director"]}}, status=401)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"director": ["you are not event admin"]}}, status=401)

        return JsonResponse({"status": True})


class EventAdministrators(APIView):

    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event": ["not found"]}}, status=404)

        event_admins = EventAdministration.objects.filter(event=event).all()
        admin_list = []

        serializer = UserSerializer

        for admin in event_admins:
            item = {}
            serialized_user = serializer(admin.user.user, context={'request': request})
            user_data = serialized_user.data
            first_name = user_data['first_name']
            last_name = user_data['last_name']
            photo = user_data['avatar']

            item['user_id'] = admin.user.user.id
            item['first_name'] = first_name
            item['last_name'] = last_name
            item['photo'] = photo
            item['is_director'] = admin.is_director
            admin_list.append(item)
        
        return JsonResponse(admin_list, safe=False)
    
    
class EventPaginator(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class EventsByOrganizer(generics.ListAPIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    serializer_class = EventModelSerializer
    pagination_class = EventPaginator

    def get_queryset(self):
        organizer_id = self.kwargs['organizer_id']
        try:
            organizer = Organizer.objects.get(id=organizer_id)
        except ObjectDoesNotExist:
            return []
        
        today = date.today()
        events = Event.objects.filter(Q(organizer=organizer)&(Q(start_event_date__gte=today)|Q(end_event_date__isnull=True)|Q(end_event_date__gte=today)))
        return events
    
    
class DraftParsing(APIView):

    authentication_classes = [SessionAuthentication,
                              BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def get(self, request, event_id):
        event = Event.objects.get(id=event_id)

        event_parameters = {}

        event_title = None
        event_description = None

        # 1 получаем id события и все языки в системе
        event_parameters['id'] = event.id
        #languages = ContentLanguageAdapter.objects.all()
        items = []

        if event.format is not None:
            event_parameters['format_id'] = event.format.id
        else:
            event_parameters['format_id'] = None

        if event.price_option is not None:
            event_parameters['price_option'] = event.price_option.id
        else:
            event_parameters['price_option'] = None

        event_parameters['price'] = int(event.price)

        if event.currency_id is not None:
            event_parameters['currency_id'] = event.currency.id
        else:
            event_parameters['currency_id'] = None
        
        event_parameters['registration_opened'] = event.registration_opened

        if event.organizer is not None:
            event_parameters['organizer_id'] = event.organizer.id
        else:
            event_parameters['organizer_id'] = None

        if event.photo is not None:
            url = event.photo.event_photo.url
            event_parameters['photo'] = url
        else:
            event_parameters['photo'] = None

        
        # 2 получаем все заголовки для события
        for language in settings.LANGUAGES:
            event.set_current_language(language[0])
            item = {}
            event_title = event.title
            event_description = event.description
            item['language_id'] = language.id
            item['title'] = event_title
            item['description'] = event_description
            items.append(item)
    
        event_parameters['descriptions'] = items

        #####

        # 3 заголовок вида спорта
        if event.sport_type:
            try:
                language = self.get_language(request=request)
                sport_title = event.sport.title
            except ObjectDoesNotExist:
                sport_title = None
            if sport_title:
                sport_content = sport_title.sport_content
                if sport_content:
                    event_parameters['sport_type'] = {'id': sport_title.sport_content.id, 
                                                    'title': sport_title.title,
                                                    'description': sport_title.description}
            else:
                event_parameters['sport_type'] = None
        ###

        # 3 Фото
        if event.photo:
            event_parameters['photo'] = event.photo.event_photo.url

        # 4 Статус
        event_parameters['status'] = event.status

        event_parameters['start_event_date'] = event.start_event_date
        event_parameters['end_event_date'] = event.end_event_date

        # 26/07/2022 - добавили новый флаг удаления
        slots = Slot.objects.filter(event=event, active=True, paid=True).all()
        slots_count = slots.count()

        referee = RefereeSlot.objects.filter(event=event).all()
        referee_count = referee.count()

        check_slots = slots_count + referee_count

        if check_slots > 0:
            event_parameters['can_delete'] = False
        else:
            event_parameters['can_delete'] = True

                
        # 5 Адресная информация
        language = self.get_language(request=request)
        if language.code == 'ru':
            if event.country:
                event_parameters['country_id'] = event.country.id
            else:
                event_parameters['country_id'] = None
            if event.region:
                event_parameters['region_id'] = event.region.id
            else:
                event_parameters['region_id'] = None
            if event.city:
                event_parameters['city_id'] = event.city.id
            else:
                event_parameters['city_id'] = None
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
        event_parameters['standart_speed_courses'] = event.standart_speed_courses
        if event.evsk:
            evskserializer = EVSKStatusSerializer
            evsk = evskserializer(event.evsk)
            data = evsk.data
            event_parameters['evsk'] = data

        # формат
        try:
            if event.format:
                format_content = Event.objects.get(format=event.format)
            else:
                format_content = None
        except ObjectDoesNotExist:
            format_content = None

        if format_content:
            event_parameters['format'] = {"id": format_content.format.id, "title": format_content.title}
        
        event_parameters['approved'] = event.approved

        # 6 проверяем на динамические свойства
        
        try:
            practical_shooting_properties = EventProperty.objects.get(event=event)
        except ObjectDoesNotExist:
            practical_shooting_properties = {}
            event_parameters['properties'] = {}
        
        event_parameters['phone'] = event.phone
        event_parameters['email'] = event.email

        if practical_shooting_properties:
            event_parameters['properties'] = {}

            # 04.03.2022 scryca: добавил дисциплины при парсинге драфта с сервера
            disciplines = practical_shooting_properties.disciplines.all()
            discipline_ids = []
            for d in disciplines:
                discipline_ids.append(d.id)

            event_parameters['properties']['disciplines'] = discipline_ids
            event_parameters['properties']['id'] = practical_shooting_properties.id                
            event_parameters['properties']['match_level'] = practical_shooting_properties.match_level
            event_parameters['properties']['exercices_amount'] = practical_shooting_properties.exercices_amount
            event_parameters['properties']['min_shoots_amount'] = practical_shooting_properties.min_shoots_amount
            event_parameters['properties']['squads_amount'] = practical_shooting_properties.squads_amount
            event_parameters['properties']['fact_squads_amount'] = Squad.objects.filter(event=event).count()
            event_parameters['properties']['shooters_in_squad'] = practical_shooting_properties.shooters_in_squad
            event_parameters['properties']['prematch'] = practical_shooting_properties.prematch
            event_parameters['properties']['number_in_calendar_plan'] = practical_shooting_properties.number_in_calendar_plan
        return JsonResponse(event_parameters, safe=False, status=200)
    

class SlotsView(APIView):

    authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated,]

    def get(self, request):
        if request.version == "1.0" or request.version is None:
            # получить все занятые слоты
            user = request.user

            if type(user) == User:
                my_slots = Slot.objects.filter(user=user, paid=True).all()
                
                if my_slots is not None:
                    serializer = SlotSerializer
                    serialized = serializer(my_slots, many=True, context={"request": request})
                    serialized = serialized.data
                else:
                    serialized = []
            else:
                serialized = []
            
            return JsonResponse(serialized, safe=False)
        else:
            # получить все занятые слоты
            user = request.user

            if type(user) == User:
                my_slots = Slot.objects.filter(user=user, paid=True).all()
                
                if my_slots is not None:
                    serializer = SlotSerializer
                    serialized = serializer(my_slots, many=True, context={"request": request})
                    serialized = serialized.data
                else:
                    serialized = []
            else:
                serialized = []
            
            return JsonResponse(serialized, safe=False)


class AllSlots(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        if request.version == "1.0" or request.version is None:
            # получить все занятые слоты
            # user = request.user
            my_events = Slot.objects.values_list('event', flat=True).distinct()

            items = []
            for event_id in my_events:
                    
                event_slots = Slot.objects.filter(event=event_id)
                serializer = SlotSerializer
                serialized = serializer(event_slots, many=True)

                items.append(serialized.data)
                
            
            return JsonResponse(items, safe=False)
        else:
            # получить все занятые слоты
            # user = request.user
            my_events = Slot.objects.values_list('event', flat=True).distinct()

            items = []
            for event_id in my_events:
                    
                event_slots = Slot.objects.filter(event=event_id)
                serializer = SlotSerializer
                serialized = serializer(event_slots, many=True)

                items.append(serialized.data)
                
            
            return JsonResponse(items, safe=False)


# ПЕРВЫЙ ВАРИАНТ РЕГИСТРАЦИИ НА СОБЫТИЕ
class RegistrationOnEvent(APIView):
    """Регистрация на событие: принимает в качестве параметров заголовок промокода и цену"""

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request, event_id):
        event_serializer = EventModelSerializer
        user_serializer = UserSerializer

        result = {}
        user = request.user
        
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "event not found"}, status=404)

        event_serialized = event_serializer(event, context={"request": request})
        user_serialized = user_serializer(user, context={"request": request})

        result['event'] = event_serialized.data
        result['user'] = user_serialized.data

        return JsonResponse(result, safe=False, status=200)


    def post(self, request, event_id):
        if request.version == "1.0" or request.version is None:
            received_json_data = json.loads(request.body)
            user = request.user
            profile = user
            event=Event.objects.get(id=event_id)

            try:
                discipline = received_json_data['discipline']
                discipline = Discipline.objects.get(id=discipline)
            except KeyError:
                return JsonResponse({"status": False, "message": "discipline is required"}, status=400)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "message": "No discipline with provided id"}, status=400)

            try:
                category = received_json_data['category']
            except KeyError:
                return JsonResponse({"status": False, "message": "category is required"}, status=400)

            try:
                power_factor = received_json_data['power_factor']
            except KeyError:
                return JsonResponse({"status": False, "message": "power factor is required"}, status=400)

            promocode_id = received_json_data.get('promocode_id')

            promocode = None
            final_price = 0
            if promocode_id:
                try:
                    promocode = PromoCode.objects.get(id=promocode_id)
                    discount = promocode.discount
                    price = int(event.price)
                    final_price = price - (price*(discount/100))
                except ObjectDoesNotExist:
                    final_price = event.price
            else:
                final_price = event.price
            
            # количество свободных и делегированных слотов больше не считаем
            free_slots = Slot.objects.filter(user__isnull=True, event=event, active=True).count()
            delegated_slots = Slot.objects.filter(user__isnull=True, promocode__isnull=False).count()

            try:
                check_slot = Slot.objects.get(user=user, event=event)
            except ObjectDoesNotExist:
                check_slot = None

            team_title = received_json_data.get('team')
    
            if check_slot is None:
                #if free_slots > 0 or delegated_slots > 0:
                    
                # если применён промокод, то проверяем, является ли промокод делегацией слота
                if promocode:
                    delegated_slot = Slot.objects.filter(Q(user__isnull=False)&Q(event=event)&Q(promocode=promocode)).first()
                else:
                    # если нет, то это не передача слота
                    delegated_slot = None
                
                # забираем свободный слот
                # 1. если есть промокод и 
                if delegated_slot is None:
                    free_slot = Slot.objects.filter(user__isnull=True, event=event, active=True).first()
                else:
                    free_slot = delegated_slot
                
                if free_slot:
                    free_slot.active = True
                    
                    # заполнение основных атрибутов слота
                    free_slot.final_price = final_price
                    free_slot.discipline = discipline
                    free_slot.category = category
                    free_slot.power_factor = power_factor

                    # обновление данных пользователя
                    user_data = received_json_data.get('user')
                    if user_data:
                        user_first_name = user_data['first_name']
                        user_last_name = user_data['last_name']
                        user_transliterated_first_name = user_data['native_firstname']
                        user_transliterated_last_name = user_data['native_lastname']
                        user_phone = user_data['phone']
                        user_birth_date = user_data['birth_date']
                        user_email = user_data['email']

                        user.first_name = user_first_name
                        user.last_name = user_last_name
                        user.email = user_email
                        user.username = user_phone

                        user.save()

                        profile.native_firstname = user_transliterated_first_name
                        profile.native_lastname = user_transliterated_last_name
                        profile.phone = user_phone
                        profile.birth_date = user_birth_date
                        
                        profile.save()

                    free_slot.user = user
                    free_slot.participant_number = Slot.objects.filter(user__isnull=False, 
                                                                    event=event, 
                                                                    active=True).all().count() + 1
                    free_slot.save()

                    # проверяем команду и если всё ок, добавляем слот в участники
                    if team_title is not None:
                        # проверяем команду на существование
                        try:
                            team_instance = Team.objects.get(event=event, title=team_title)
                            flag = True
                        except ObjectDoesNotExist:
                            flag = False
                        # если команда не существует, создаём новую
                        if flag is False:
                            new_team = Team.objects.create(event=event, 
                                                        title=team_title, 
                                                        discipline=discipline)
                            new_team.save()
                            # устанавливаем в слот команду
                            free_slot.team = new_team
                            free_slot.save()
                        else:
                            # если команда существует, посчитаем количество 
                            team_slots = Slot.objects.filter(team=team_instance).all()
                            slots_amount_in_team = team_slots.count()
                            # если слотов в команде меньше 5, присваиваем команду слоту
                            if slots_amount_in_team < 4:
                                free_slot.team = team_instance
                                free_slot.save()
                else:
                    return JsonResponse({"status": False, "message": "No free slots in event"}, status=404)
            
                # создаём системное событие на регистраци
                try:
                    language = self.get_language(request=request)
                    create_system_event_object(user, 'user_registered_on_event', {'user_id': user.id, 'id': event.id})
                except:
                    pass

                return JsonResponse({"status": True, "slot_id": f"{free_slot.id}"})
            else:
                return JsonResponse({"status": False, "message": "You are already registered on event"}, status=400)


class ApplyPromocode(APIView):
    
    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, event_id):
        received_json_data = json.loads(request.body)

        # получаем цену и заголовок промокода
        # old_price = received_json_data['price']
        promocode_title = received_json_data['promocode']

        # ищем промокод в списке доступных для мероприятия
        event = Event.objects.get(id=event_id)
        promocode_instance = None
        try:
            promocode_instance = PromoCode.objects.get(title=promocode_title, related_event=event)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Promocode is not found"}, status=404)
        used = Slot.objects.filter(promocode=promocode_instance, event=event).count()

        # проверяем, активен ли промокод, не наступила ли дата окончания действия промокода и не исчерпан ли лимит использования промокода
        finish_date = promocode_instance.finish_date if promocode_instance.finish_date is not None else date(year=2999, day=1, month=1)
        if promocode_instance.active and finish_date >= date.today() and used < promocode_instance.limit:
            discount = promocode_instance.discount
            # из старой цены вычитаем цену, умноженную на коэффициент по промокоду
            price = event.price
            coefficient = discount/100
            end_discount = int(price)*coefficient
            # получаем финальную цену
            price = int(price) - int(end_discount)
        elif promocode_instance.active == False:
            return JsonResponse({"status": False, "message": "Promocode is inactive"}, status=400)
        elif finish_date < date.today():
            return JsonResponse({"status": False, "message": "Promocode is outdated"}, status=400)
        elif promocode_instance.limit == used:
            return JsonResponse({"status": False, "message": "Promocode limit is reached"}, status=400)
        serializer = PromocodeSerializer
        serialized = serializer(promocode_instance)
        data = serialized.data
        return JsonResponse({"status": True, "message": f"Promocode {promocode_title} is succesfully applied", "price": price, "schema": data})


class DelegateSlot(APIView):
    """"Делегирование слота другому пользователю
    через создание нового промокода"""
    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, slot_id):
        # если слот пользователя, то зачищаем параметры
        user = request.user      
        try:
            slot = Slot.objects.get(id=slot_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Slot with this id not found"}, status=404)
        slot_user = slot.user

        if user == slot_user:
            slot.user = None
            #slot.save()
        elif slot_user is None:
            return JsonResponse({"status": False, "message": "This promocode not applied for user"}, status=400)
        else:
            # если пользователь не совпадает с текущим пользователем, отказываем
            return JsonResponse({"status": False, "message": "This slot is applied for another user!"}, status=401)
        
        # генерируем промокод
        promocode_title = ''

        for i in range(0, 4): promocode_title += random.choice(string.ascii_letters).upper()
        for i in range(0, 4): promocode_title += random.choice(string.digits)

        promocode = PromoCode.objects.create(related_event=slot.event, title=promocode_title, discount=100, limit = 1, active=True)
        promocode.save()

        # подготавливаем слот для регистрации по промокоду
        slot.promocode = promocode
        slot.active = False
        slot.save()
        return JsonResponse({"status": True, "promocode_id": promocode.id, "promocode_title": promocode.title})
        


# добавить администратора события в системе
class AddEventAdmin(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, event_id, user_id):
        data = request.data

        is_director = data.get('is_director')

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event": ["not found"]}}, status=404)

        try:
            user = User.objects.get(id=user_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"user": ["not found"]}}, status=404)

        user_profile = request.user

        check = EventAdministration.objects.filter(user=user_profile, event=event)
        count = check.count()

        if count == 0:
            new_administration_record = EventAdministration.objects.create(user=user_profile, event=event)

            if is_director is True:
                old_director = EventAdministration.objects.filter(event=event, is_director=True).all()
                for director_record in old_director:
                    director_record.is_director = False
                    director_record.save()

                new_administration_record.is_director = True
                new_administration_record.save()

            try:
                create_system_event_object(request.user, 'event_admin_added' ,json_content={'id': event_id, 'target_user': user_profile.user.id})
            except: # noqa
                pass
        else:
            return JsonResponse({"status": False, "errors": {"admin": ["already exist"]}}, status=400)

        return JsonResponse({"status": True})

    def delete (self, request, event_id, user_id):

        request_user = request.user
    
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event": ["not found"]}}, status=404)

        admin_record = EventAdministration.objects.get(user=request_user, event=event)

        try:
            target_user = User.objects.get(id=user_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"user": ["not found"]}}, status=404)

        if admin_record.is_director or target_user == request_user:
            try:
                target_profile = request.user
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"profile": ["not found"]}}, status=404)
            try:
                event_admin = EventAdministration.objects.filter(event=event, user=target_profile).all()
                event_admin.delete()
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"administrator": ["not found"]}}, status=404)
            return JsonResponse({"status": True}, status=200)
        else:
            return JsonResponse({"status": False, "errors": {"is_director": ["you are not director"]}}, status=401)



class ApproveEvent(APIView):
    # подтверждение события.
    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def put(self, request, event_id):
      
        event = Event.objects.get(id=event_id)
        event.moderated = False
        event.approved = True
        event.save()
        # создаём системное событие для мероприятия
        try:
            create_system_event_object(request.user, 'event_approved', {'id': event.id})
        except:
            pass

        return JsonResponse({"status": True})


class DismissEvent(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]


    def put(self, request, event_id):
        data = request.data

        dismiss_reason = data.get('dismiss_reason')

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False,
                                "errors": {"event_id": ['not found']}},
                                status=404)
        
        if dismiss_reason:
            event.dismissed = True
            event.moderated = False
            event.approved = False
            event.dismiss_reason = dismiss_reason
        else:   
            event.status = Event.DRAFT
        # event_admins = EventAdministration.objects.filter(event=event).all()
        # event_admins.delete()
        
        event.save()

        # создаём системное событие для мероприятия
        try:
            create_system_event_object(request.user, 'event_changed', {'id': event.id})
        except:
            pass

        return JsonResponse({"status": True})



# регистрация от лица другого пользователя (не потребовалась)
class RegisterSlotByOtherUser(APIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, ]

    def _get_event(self, event_id):
        event = Event.objects.filter(id=event_id).first()
        return event

    def _get_user(self, user_id):
        user = User.objects.filter(id=user_id).first()
        return user

    def _get_discipline(self, discipline_id):
        discipline = Discipline.objects.filter(id=discipline_id).first()
        return discipline

    def _get_promocode(self, promocode_id):
        promocode = PromoCode.objects.filter(id=promocode_id).first()
        return promocode

    def _create_team(self, event, discipline, team_title):
        new_team = Team.objects.create(title=team_title, event=event, discipline=discipline)
        new_team.save()
        return new_team

    def _check_team(self, event, team_title):
        team = Team.objects.filter(event=event, title=team_title).first()
        return team

    @transaction.atomic
    def post(self, request, event_id, user_id):
        data = request.data
        
        errors = {}

        user = self._get_user(user_id)

        if user is None:
            errors['user'] = ['user not found']
            return JsonResponse({"status": False, 'errors': errors}, status=404)

        event = self._get_event(event_id)
        
        if event is None:
            errors['event'] = ['event is not found']
            return JsonResponse({"status": False, 'errors': errors}, status=404)

        
        division = data['division']
        competition_type = data['competition_type']
        promocode_id = data['promocode_id']
        if promocode_id is not None:
            try:
                promocode = PromoCode.objects.get(id = promocode_id)
            except ObjectDoesNotExist:
                promocode = None

        discipline = Discipline.objects.filter(division__id=division,
                                                competition_type=competition_type).first()
        if discipline is None: errors['discipline'] = ['discipline is required']

        category = data['category']
        if category not in range(1, 7): errors['category'] = ['category must be 1-6 (SJ - SS)']

        power_factor = data['power_factor']
        if power_factor not in [1, 2]: errors['power_factor'] = ['power factor must be 1 or 2 (MIN - MAJ)']

        it_has_slot = Slot.objects.filter(event=event, user=user, paid=True, active=True).first()
        if it_has_slot is not None:
            return JsonResponse({"status": False, "errors": {"user": ["user already has slot"]}}, status=400)

        # создание слота
        participant_number = Slot.objects.all().count()

        new_slot = Slot.objects.create(user=user,
                                        event=event,
                                        promocode=promocode,
                                        discipline=discipline,
                                        category=category,
                                        power_factor=power_factor,
                                        final_price=0,
                                        participant_number=participant_number + 1,
                                        currency = event.currency,
                                        active=True,
                                        paid=True)
        new_slot.save()

        # добавление команды
        team_title = data.get('team_title')
        if team_title is not None:
            check = self._check_team(event, team_title)
            if check is None:
                new_team = Team.objects.create(title=team_title,
                                                discipline=discipline,
                                                event=event)
                new_team.save()
            else:
                teammates = Slot.objects.filter(team=check, event=event).count()
                if teammates < 4:
                    new_slot.team = check
                    new_slot.save()

        return JsonResponse({"status": True, "slot_id": new_slot.id})
    
    
# вернуть слот 
class ReturnSlotAsDirector(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, slot_id):
        slot = Slot.objects.get(id=slot_id)
        order = OrderItem.objects.filter(object_id=slot_id,
                                        object_type='Slot').last()
        order_id = order.order_id
        
        payment_record = TransactionHistory.objects.filter(order_id=order_id.id, 
                                                            operation="finish_authorize",
                                                            success=True).last()
        # response = payment_record.response                    

        payment_id = payment_record.payment_id

        merchant = TinkoffMerchantAPI(terminal_key=TINKOFF_TERMINAL_KEY,
                                    secret_key=TINKOFF_PASSWORD)

        response = merchant.cancel(PaymentId=str(payment_id))
        answer = response.json()

        order_id = answer.get('OrderId')
        success = answer.get('Success')
        status = answer.get('Status')
        payment_id = answer.get('PaymentId')
        error_code = answer.get('ErrorCode')
        message = answer.get('Message')
        details = answer.get('Details')
        original_amount = answer.get('OriginalAmount')
        new_amount = answer.get('NewAmount')

        try:
            bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.CANCEL,
                                                            information_type=TransactionHistory.BANK_RESPONSE,
                                                            order_id = order_id,
                                                            success = success,
                                                            status = status,
                                                            payment_id = payment_id,
                                                            error_code = error_code,
                                                            message = message,
                                                            details = details,
                                                            response = answer)
            bankresponse.save()
        except Exception:
            pass
        
        if success is True:
            slot.user = None
            slot.paid = False
            slot.save()

            return JsonResponse({"status": True})
        else:
            if message is not None:
                return JsonResponse({"status": False, 'errors': {'message': [f"{message}"]}})
            else:
                return JsonResponse({"status": False})


# Обновление слота
class SlotUpdateView(APIView):

    def put(self, request, slot_id):
        data = request.data

        # discipline_id = data.get('discipline_id')
        division = data['division']
        competition_type = data['comptetition_type']
        team_title = data.get("team_title")
        category = data.get('category')
        power_factor = data.get('power_factor')

        if division is not None and competition_type is not None:
            try:
                division = Division.objects.get(id=division)
                discipline = Discipline.objects.filter(division=division,
                                                        comptetition_type=competition_type)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, 
                                    "errors": {"division": ["not found"]}}, 
                                    status=404)

        
        try:
            slot = Slot.objects.get(id=slot_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"slot_id": ['not found']}},
                                status=404)
        if category:
            if category < 1 or category > 6:
                return JsonResponse({"status": False, "errors": {"category": ['1 - 6']}},
                                    status=400)
        
        if power_factor:
            if power_factor not in (1, 2):
                return JsonResponse({"status": False, "errors": {"power_factor": ['1 or 2']}},
                                    status=404)

        if team_title:
            try:
                team = Team.objects.get(title=team_title)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"team": ['not exist']}},
                                status=404)

        # if discipline_id: slot.discipline = discipline
        slot.discipline = discipline
        if category: slot.category = category
        if power_factor: slot.power_factor = power_factor
        if team_title: slot.team = team
        
        slot.save()

        return JsonResponse({"status": True})
    
    
    # удалить судью
class DeleteReferee(APIView):
    """Удалить назначенного на событие судью"""
    def delete(self, request, event_id, user_id):
        try:
            user = User.objects.get(id=user_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"user": ['not found']}},
                                status=404)

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event": ['not found']}},
                                status=404)

        
        referee_record = EventRefereeInvite.objects.filter(Q(user=user)& 
                                                        Q(event=event)&
                                                        (
                                                        Q(status=EventRefereeInvite.APPROVED)|
                                                        Q(status=EventRefereeInvite.MODERATED)
                                                        )).all()
        referee_record.delete()

        referee_slots = RefereeSlot.objects.filter(user=user, event=event).all()
        referee_slots.delete()

        return JsonResponse({"status": True})


class EventDraft(APIView):

    authentication_classes = [TokenAuthentication]

    def get(self, request, event_id):
        serializer = EventShortSerializer
        try:
            event = Event.objects.get(id = event_id)
        except ObjectDoesNotExist:
            event = None

        if event is not None:
            serialized = serializer(event, context={'request': request})
            data = serialized.data
        else:
            data = []
        return JsonResponse(data)