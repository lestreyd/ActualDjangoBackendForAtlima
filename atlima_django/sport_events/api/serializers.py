from ..models import EventFormat, Slot, EventEVSKStatus, Squad, EventProperty, Event
from rest_framework import serializers
from atlima_django.users.api.serializers import UserSerializer
from atlima_django.money.api.serializers import PromocodeSerializer
from atlima_django.ipsc.api.serializers import DisciplineSerializer, PropertyWeaponSerializer
from atlima_django.ipsc.models import SlotResult
from atlima_django.location.api.serializers import CitySerializer, CountrySerializer, RegionSerializer
from atlima_django.referee.models import EventRefereeInvite, RefereeSlot
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.users.models import User
from atlima_django.system.models import SystemEvent, SystemEventType
from django.db.models import Q, F
from atlima_django.sport.api.serializers import SportSerializer
from django.conf import settings
from atlima_django.money.api.serializers import CurrencySerializer, PriceOptionSerializer
from atlima_django.referee.api.serializers import RefereeViewSerializer, RefereeInviteSerializer
from atlima_django.sport_events.api.serializers import EventOrganizerSerializer
from atlima_django.sport_events.models import UserInterestedIn, EventAdministration
from atlima_django.ipsc.models import (SlotResult, AggregatedCourseResultForSlot, Course, Division, Weapon,
                                    SlotSerializedWithResults)
from atlima_django.ipsc.api.serializers import PSPropertySerializer
from atlima_django.ipsc.api.serializers import (
    GuncheckViewSerializer,
    DisqualificationViewSerializer,
    TargetResultViewSerializer,)


# Сериализатор формата соревнований
# от клубного матча до соревнования
class EventFormatSerializer(serializers.Serializer):

    id = serializers.IntegerField()
    title = serializers.CharField(source='default_title')


# базовый сериаализатор слота
class SlotSerializer(serializers.ModelSerializer):
    
    user = UserSerializer()
    promocode = PromocodeSerializer()
    event_id = serializers.IntegerField(source='event.id')
    discipline = DisciplineSerializer()
    participant_number = serializers.SerializerMethodField('get_participant_number')
    overall = serializers.SerializerMethodField('get_overall')

    def get_overall(self, obj):
        return {
            "percentage": obj.percentage,
            "stage_points": obj.stage_points,
            "points": obj.points
        }
    
    def get_details(self, obj):
        slot_results = SlotResult.objects.filter(slot=obj).all()
        results = []
        for result in slot_results:
            course_id = result.course.id
            course_points = result.course_points
            stage_points = result.stage_points
            hit_factor = result.hit_factor
            results.append(
                {
                    "course_id": course_id,
                    "course_points": course_points,
                    "stage_points": stage_points,
                    "hit_factor": hit_factor
                }
            )
        return results

    def get_slots_for_event(self, obj):

        return Slot.objects.filter(event=obj.event, paid=True, active=True, user__isnull=False).order_by('created')

    def get_participant_number(self, obj):
        
        slots = self.get_slots_for_event(obj)
        counter = 0
        for slot in slots:
            counter += 1
            if slot.id == obj.id:
                return counter
        return 0
    class Meta:
        model = Slot
        exclude = ['event', 'participant_group']
        

# сериализатор слота (краткий вывод)
class SlotResultShortSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    course_points = models.FloatField(default=0)
    stage_points = models.FloatField(default=0)
    hit_factor = models.FloatField(default=0)

    class Meta:
        model = SlotResult
        exclude = ['slot', 'course']
        

# сериализатор ЕВСК для события
# ЕВСК может иметь региональный, федеральный
# и неофициальный статус        
class EVSKStatusSerializer(serializers.ModelSerializer):
    """Сериализатор справочника статусов ЕВСК"""
    class Meta:
        model = EventEVSKStatus
        fields = '__all__'


# сериализатор сквода в судействе
class RefereeSquadSerializer(serializers.ModelSerializer):

    squad_id = serializers.IntegerField(read_only=True, source='id')
    event_id = serializers.IntegerField(source='event.id')

    class Meta:
        model = Squad
        exclude = ['event', 'updated']


# сериализатор сквода
class SquadSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    event_id = serializers.IntegerField(source='event.id')

    class Meta:
        model = Squad
        exclude = ['event', 'updated']


class EventMenuSerializer():
    
    id = serializers.IntegerField(read_only=True)
    photo = serializers.SerializerMethodField('get_photo_url')
    title = serializers.SerializerMethodField('get_relative_language_title')
    start_event_date = serializers.DateTimeField()
    end_event_date = serializers.DateTimeField()
    city = CitySerializer()
    weapons = serializers.SerializerMethodField('get_weapons')
    match_level = serializers.SerializerMethodField('get_match_level')
    interested = serializers.SerializerMethodField('get_interested')
    registered = serializers.SerializerMethodField('get_registered')
    referee = serializers.SerializerMethodField('get_is_referee')
    role = serializers.SerializerMethodField('get_referee_role')
    admin = serializers.SerializerMethodField('get_is_admin')
    director = serializers.SerializerMethodField('get_is_director')
    invited = serializers.SerializerMethodField('get_invited')
    invited_to_participate = serializers.SerializerMethodField('get_invited_participant')
    requested = serializers.SerializerMethodField('get_requested')
    evsk = EVSKStatusSerializer()

    def get_city(self, obj):
        serializer = CitySerializer
        serialized = serializer(obj).data
        return serialized


    def get_requested(self, obj):
        user = self._user(obj)
        if type(user) == User:
            requested = EventRefereeInvite.objects.filter(event=obj).filter(Q(user=F('created_by'))&Q(user=user)&Q(status=EventRefereeInvite.WAITING)).first()
            if requested:
                return True
        return False

    def _user(self, obj):
        request = self.context.get('request', None)
        if request:
            return request.user

    def get_invited_participant(self, obj):
        user = self._user(obj)
        if type(user) == User:
            system_event = SystemEventType.objects.get(title='event_participant_invite')

            invited = SystemEvent.objects.filter(user=user, 
                                                system_type=system_event,
                                                json_attributes__id=obj.id).first()
            if invited:
                return True
        return False
    
    def get_interested(self, obj):
        user = self._user(obj)
        if type(user) == User:
            if user in obj.interested:
                return True
        return False

    def get_invited(self, obj):
        user = self._user(obj)
        if type(user) == User:
            invited = EventRefereeInvite.objects.filter(~Q(user=F('created_by'))&Q(user=user)&Q(event=obj)&Q (status=EventRefereeInvite.WAITING)).first()
            if invited:
                return True
        return False

    def get_registered(self, obj):
        user = self._user(obj)
        if type(user) == User:
            registered = Slot.objects.filter(user=user, event=obj, paid=True).first()
            if registered:
                return True
        return False

    def get_is_referee(self, obj):
        user = self._user(obj)
        if type(user) == User:
            referee = RefereeSlot.objects.filter(user=user, event=obj).first()
            if referee:
                return True
        return False
    
    def get_referee_role(self, obj):
        user = self._user(obj)
        if type(user) == User:
            referee = RefereeSlot.objects.filter(user=user, event=obj).first()
            if referee:
                role = referee.role
                return role
        return 0
    
    def get_is_admin(self, obj):
        user = self._user(obj)
        if type(user) == User:
            if user in obj.administrators:
                return True
        return False

    def get_is_director(self, obj):
        user = self._user(obj)
        if type(user) == User:
            if user in obj.administrators:
                return True
        return False

    def get_weapons(self, obj):
        weapons = []
        try:
            properties = EventProperty.objects.get(event=obj)
            disciplines = properties.disciplines.all()
            for discipline in disciplines:
                weapon = discipline.division.weapon
                serializer = PropertyWeaponSerializer
                serialized = serializer(weapon)
                if serialized.data not in weapons:
                    weapons.append(serialized.data)
            return weapons
        except ObjectDoesNotExist:
            return weapons

    def get_match_level(self, obj):
        try:
            properties = EventProperty.objects.get(event=obj)
        except ObjectDoesNotExist:
            return None
        return properties.match_level

    def get_photo_url(self, obj):
        if obj.photo:
            url = obj.photo.event_photo.url
        else:
            url = None
        return url


    class Meta:
        model = Event
        exclude = ['format', 'price_option', 'price', 'currency',
                'organizer', 'country', 'region', 
                'site', 'slug', 'standart_speed_courses',
                'phone', 'email', 'has_results', 'created', 'updated',
                'created_by']


class EventPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventProperty
        fields = '__all__'
        

class PSPropertySerializer2(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    disciplines = serializers.SerializerMethodField('get_disciplines')

    def get_disciplines(self, obj):
        disciplines = obj.disciplines.all()
        a = []
        for d in disciplines:
            a.append(d.id)
        return a

    class Meta:
        model =  EventProperty
        fields = '__all__'



class EventShortSerializer(serializers.ModelSerializer):
    
    id = serializers.IntegerField(read_only=True)
    format_id = serializers.SerializerMethodField('get_format')
    sport_type = SportSerializer()
    price_option = serializers.SerializerMethodField('get_price_option')
    price = serializers.IntegerField()
    currency_id = serializers.SerializerMethodField('get_currency')
    organizer_id = serializers.SerializerMethodField('get_organizer')
    photo = serializers.SerializerMethodField('get_photo_url')
    titles = serializers.SerializerMethodField('get_descriptions')

    status = serializers.CharField()
    start_event_date = serializers.DateTimeField()
    end_event_date = serializers.DateTimeField()

    country_id = serializers.SerializerMethodField('get_country')
    region_id = serializers.SerializerMethodField('get_region')
    city_id = serializers.SerializerMethodField('get_city')

    location = serializers.CharField()
    site = serializers.CharField()
    slug = serializers.SlugField()
    standart_speed_courses = serializers.BooleanField()
    approved = serializers.BooleanField()
    phone = serializers.CharField()
    email = serializers.CharField()
    properties = serializers.SerializerMethodField('get_properties')
    invited = serializers.SerializerMethodField('get_invited_as_referee')
    invited_to_participate = serializers.SerializerMethodField('get_invited_participant')
    requested = serializers.SerializerMethodField('get_requested')
    evsk = EVSKStatusSerializer()

    def _user(self, obj):
        request = self.context.get('request', None)
        if request:
            return request.user

    def get_invited_as_referee(self, obj):
        user = self._user(obj)
        if type(user) == User:
            invited = EventRefereeInvite.objects.filter(~Q(user=F('created_by'))&Q(user=user)&Q(event=obj)&Q (status=EventRefereeInvite.WAITING)).first()
            if invited:
                return True
        return False

    
    def get_invited_participant(self, obj):
        user = self._user(obj)
        if type(user) == User:
            system_event = SystemEventType.objects.get(title='event_participant_invite')

            invited = SystemEvent.objects.filter(user=user, 
                                                system_type=system_event,
                                                json_attributes__id=obj.id).first()
            if invited:
                return True
        return False

    
    def get_requested(self, obj):
        user = self._user(obj)
        if type(user) == User:
            requested = EventRefereeInvite.objects.filter(event=obj).filter(Q(user=F('created_by'))&Q(user=user)&(Q(status=EventRefereeInvite.WAITING))).first()
            if requested:
                return True
        return False


    def get_photo_url(self, obj):
        url = obj.photo.event_photo.url if obj.photo else None
        return url

    def get_descriptions(self, obj):
        languages = settings.LANGUAGES
        descriptions = []
        for index, language in enumerate(languages):
            item = {}
            event_title = obj.title
            event_description = obj.description
            item['language_id'] = language.id
            item['title'] = event_title
            item['description'] = event_description
            descriptions.append(item)
        return descriptions

    def get_properties(self, obj):
        properties = EventProperty.objects.filter(event=obj).first()
        if properties is not None:
            serializer = PSPropertySerializer2
            serialized = serializer(properties, context={'request': self.context['request']})
            return serialized.data
        return {}

    def get_format(self, obj):
        if obj.format:
            return obj.format.id
        return None
    
    def get_city(self, obj):
        if obj.city is not None:
            return obj.city.id
        return None

    def get_country(self, obj):
        if obj.country is not None:
            return obj.country.id
        return None
    
    def get_region(self, obj):
        if obj.region is not None:
            return obj.region.id
        return None

    def get_price_option(self, obj):
        if obj.price_option is not None:
            return obj.price_option.id
        return None

    def get_currency(self, obj):
        if obj.currency is not None:
            return obj.currency.id
        return None

    def get_organizer(self, obj):
        if obj.organizer is not None:
            return obj.organizer.id
        return None

    class Meta:
        model = Event
        fields = '__all__'
        
        
class ParticipantSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)

    first_name = serializers.CharField(max_length=256, required=False)
    last_name = serializers.CharField(max_length=256, required=False)
    strong_hand = serializers.SerializerMethodField('get_strong_hand')
    country_code = serializers.SerializerMethodField('get_country_code')

    def get_country_code(self, obj):
        profile = obj
        if profile:
            if profile.country:
                country = profile.country
                alpha2 = country.alpha2
            else:
                alpha2 = None
        else:
            alpha2 = None
        return alpha2
    
    def get_strong_hand(self, obj):
        try:
            profile = obj
            strong_hand = profile.strong_hand
        except:
            strong_hand = ""

        return strong_hand
        
        
class SlotSerializerWithResults(serializers.ModelSerializer):

    user = serializers.SerializerMethodField('get_user_field')
    event_id = serializers.SerializerMethodField('get_event_id')
    # discipline = DisciplineSerializer()
    discipline_id = serializers.IntegerField(source='slot.discipline.id')
    results = serializers.SerializerMethodField("get_slot_resuults")
    
    def get_event_id(self, obj):
        slot_result = SlotResult.objects.get(obj)
        slot = slot_result.slot
        event_id = slot.event.id
        return event_id

    def get_user_field(self, obj):
        slot = Slot.objects.filter(id=obj).first()
        user = slot.user
        serializer = ParticipantSerializer
        serialized = serializer(user).data
        return serialized


    def get_slot_results(self, obj):
        slot_results = SlotResult.objects.filter(slot__squad=obj).order_by('-hit_factor').all()
        slot_results_on_squad = []

        if slot_results is not None: 
            for index, slot_result in enumerate(slot_results):
                slot_results_on_squad.append(
                {"percentage": slot_result.percentage,
                "stage_points": slot_result.stage_points,
                "hit_factor": slot_result.hit_factor,
                "points": slot_result.points,
                "place": index}
                )
        return slot_results_on_squad

    class Meta:
        model = Slot
        exclude = ['event', 'participant_group', 'promocode', 'active', 'final_price', 'currency', 'discipline']




class EventModelSerializer(serializers.ModelSerializer):

    title = serializers.SerializerMethodField('get_relative_language_title')
    description = serializers.SerializerMethodField('get_description')
    format = EventFormatSerializer()
    sport_type = SportSerializer()
    photo = serializers.SerializerMethodField('get_photo_url')

    country = serializers.SerializerMethodField('get_country')
    region = serializers.SerializerMethodField('get_region')
    city = serializers.SerializerMethodField('get_city')
    
    organizer = EventOrganizerSerializer()
    currency = CurrencySerializer()
    price_option = PriceOptionSerializer()

    properties = serializers.SerializerMethodField('get_properties')
    weapons = serializers.SerializerMethodField('get_weapons')

    start_event_date = serializers.DateTimeField()
    end_event_date = serializers.DateTimeField()

    squads = serializers.SerializerMethodField('get_event_squads')
    admins = serializers.SerializerMethodField('get_event_administrators')
    referee_requests = serializers.SerializerMethodField('get_event_referees')
    interested = serializers.SerializerMethodField('get_interested')
    invited = serializers.SerializerMethodField('get_invited_as_referee')
    invited_to_participate = serializers.SerializerMethodField('get_invited_participant')

    creator = UserSerializer(source='created_by')
    evsk = EVSKStatusSerializer()

    class Meta:
        model = Event
        exclude = ['created_by']

    def get_invited_participant(self, obj):
        user = self._user(obj)
        if type(user) == User:
            system_event = SystemEventType.objects.get(title='event_participant_invite')

            invited = SystemEvent.objects.filter(user=user, 
                                                system_type=system_event,
                                                json_attributes__id=obj.id).first()
            if invited:
                return True
        return False

    def _user(self, obj):
        request = self.context.get('request', None)
        if request:
            return request.user
    
    def get_interested(self, obj):
        user = self._user(obj)
        if type(user) == User:
            interested = UserInterestedIn.objects.filter(user=user, event=obj).first()
            if interested:
                return True
        return False

    def get_invited_as_referee(self, obj):
        user = self._user(obj)
        if type(user) == User:
            invited = EventRefereeInvite.objects.filter(~Q(user=F('created_by'))&Q(user=user)&Q(event=obj)&Q (status=EventRefereeInvite.WAITING)).first()
            if invited:
                return True
        return False

    def get_description(self, obj):
        return obj.description

    def get_photo_url(self, obj):
        url = obj.photo.event_photo.url if obj.photo else None
        return url

    def get_title(self, obj):
        return obj.title

    def get_country(self, obj):
        serializer = CountrySerializer
        if obj.country is None:
            serialized = serializer(obj.country)
        return serialized.data
            

    def get_region(self, obj):
        serializer = RegionSerializer
        if obj.region is not None:
            return serializer(obj.region)
        
    def get_city(self, obj):
        serializer = CitySerializer
        if obj.city:
            serializer = serializer(obj.city)

    def get_properties(self, obj):
        properties = EventProperty.objects.filter(event=obj).first()
        if properties is not None:
            serializer = PSPropertySerializer
            serialized = serializer(properties, context={'request': self.context['request']})
            return serialized.data
        return {}


    def get_event_squads(self, obj):
        """Функция для загрузки списка скводов и листа ожидания
        Все слоты, в которых не назначены скводы, относятся к листу ожидания."""
        # забираем все скводы, относящиеся к этому мероприятию
        squads = Squad.objects.filter(event=obj).order_by('squad_number')
        result = []
        # 1. прочитать все скводы и добавить по скводам всех участников (слоты)
        squad_serializer = SquadSerializer
        slot_serializer = SlotSerializer
        for squad in squads:
            # сериализация сквода
            serialized = squad_serializer(squad, context={'request': self.context['request']})
            data = serialized.data
            # если есть слоты, добавим в сериализованное значение
            # ВНИМАНИЕ: здесь, возможно, нужна проверка на пустого пользователя
            slots = Slot.objects.filter(Q(event=obj)&Q(squad=squad)&Q(paid=True)).all()
            data['slots'] = []
            
            if slots.count() > 0:
                serialized = slot_serializer(slots, many=True, context={'request': self.context['request']})
                data['slots'] = serialized.data

            # добавляем полученные данные в список
            result.append(data)

        # сформируем лист ожидания (это все слоты участников мероприятия, где не установлен сквод)
        # пользователь должен быть установлен на слоте
        waiting_list_slots = Slot.objects.filter(Q(event=obj)&Q(squad__isnull=True)&Q(user__isnull=False)&Q(paid=True))

        serializer = SlotSerializer
        serialized = serializer(waiting_list_slots, many=True, context={'request': self.context['request']})

        # соберём всю информацию по слотам в единый словарь
        combined = {}
        combined['assigned'] = result
        combined['not_assigned'] = serialized.data

        return combined


    def get_event_administrators(self, obj):
        """Функция возвращает список администраторов события"""
        event_admins = EventAdministration.objects.filter(event=obj).all()
        result = []
        for event_admin in event_admins:
            item = {}

            id = event_admin.user.user.id
            first_name = event_admin.user.user.first_name
            last_name = event_admin.user.user.last_name
            is_director = event_admin.is_director
            photo = event_admin.user.profile_photo
            if photo is not None:
                image_url = photo.profile_photo.url
            else:
                image_url = None
            item = {"user_id": id, "first_name": first_name, "last_name": last_name, "photo": image_url, "is_director": is_director}
            result.append(item)
        return result


    def get_event_referees(self, obj):
        """Функция возвращает список судей мероприятия"""
        serializer = RefereeInviteSerializer
        result = {}
        
         # сначала отфильтруем список всех, кто уже подтверждён как судья на мероприятие
        approved = EventRefereeInvite.objects.filter(Q(event=obj)&(Q(status=EventRefereeInvite.APPROVED)|Q(status=EventRefereeInvite.MODERATED)))
        serialized = serializer(approved, many=True)
        result['approved'] = serialized.data

        # получим список всех, кто заявлялся сам как судья на мероприятие
        requested = EventRefereeInvite.objects.filter(event=obj).filter(Q(user=F('created_by'))&(~Q(status=EventRefereeInvite.DISMISSED)&~Q(status=EventRefereeInvite.APPROVED)&~Q(status=EventRefereeInvite.MODERATED)))
        serialized = serializer(requested, many=True)
        result['requested'] = serialized.data

        # и список тех, кого заявлял Главный судья или Заместитель главного судьи
        invited = EventRefereeInvite.objects.filter(event=obj).filter(~Q(user=F('created_by'))&Q(status=EventRefereeInvite.WAITING))
        serialized = serializer(invited, many=True)
        result['invited'] = serialized.data

        return result

    
    def get_weapons(self, obj):
        """Функция возвращает список доступных видов оружия"""
        serializer = PropertyWeaponSerializer
        try:
            properties = EventProperty.objects.get(event=obj)
        except ObjectDoesNotExist:
            return []

        ids = properties.disciplines.values_list('division', flat=True).distinct()
        weapons_ids = Division.objects.filter(id__in=ids).values_list('weapon', flat=True).distinct()
        
        if ids.count() > 0:
            weapons = Weapon.objects.filter(id__in=weapons_ids)
            serialized = serializer(weapons, many=True,  context={'request': self.context['request']})
            result = serialized.data
        else:
            result = []

        return result
    
    
class RefereeViewSquadSerializer(serializers.ModelSerializer):
    """Сериализатор для представления Судейство"""
    # количество результатов по упражнениям 
    id = serializers.IntegerField(source="id")
    result_status = serializers.SerializerMethodField("get_result_status")
    #slots = serializers.SerializerMethodField('get_results_by_slot')
    results = serializers.SerializerMethodField('get_slot_results')

    def get_results_by_slot(self, obj):
        """получение результатов по слотам"""
        slots_in_squad = Slot.objects.filter(squad=obj).all()
        result_data_by_slot = []
        serializer = SlotSerializerWithResults
        serialized = serializer(
            slots_in_squad, 
            many=True, 
            context={'request': self.context['request']})
        slot_data = serialized.data
        
        for slot in slot_data:
            dq_dns_types = [AggregatedCourseResultForSlot.DNS, AggregatedCourseResultForSlot.DQ]
            
            dq_mark = AggregatedCourseResultForSlot.objects.filter(
                cancellation__in=dq_dns_types, 
                slot__id=slot['id'], active=True).all()
            serializer = DisqualificationViewSerializer
            
            if dq_mark is not None:
                serialized = serializer(dq_mark, context={'request': self.context['request']}, many=True)
                slot_data['DQ'] = serialized.data
            else:
                slot_data['DQ'] = None

            dns_mark = AggregatedCourseResultForSlot.objects.filter(
                result_type=AggregatedCourseResultForSlot.DISQUALIFICATION, 
                slot__id=slot['id'], 
                cancellation=AggregatedCourseResultForSlot.DNS, 
                active=True).all()
            serializer = DisqualificationViewSerializer
            if dns_mark is not None:
                serialized = serializer(
                    dns_mark, 
                    context={'request': self.context['request']}, 
                    many=True)
                slot_data['DNS'] = serialized.data
            else:
                slot_data['DNS'] = None
            
            guncheck_result = AggregatedCourseResultForSlot.objects.filter(
                result_type=AggregatedCourseResultForSlot.GUNCHECK, 
                slot__id=slot['id'], active=True).first()
            guncheck_serializer = GuncheckViewSerializer
            if guncheck_result is not None:
                guncheck_view = guncheck_serializer(guncheck_result)
                slot_data['guncheck'] = guncheck_view.data
            else:
                slot_data['guncheck'] = None

            results = AggregatedCourseResultForSlot.objects.filter(
                result_type=AggregatedCourseResultForSlot.COURSE_TARGET_RESULT, 
                slot__id=slot['id'], 
                active=True).all()

            courses = Course.objects.filter(event=slot.event).all()
            camount = courses.count()
            slot_data['courses_overall'] = camount
            result_serializer = TargetResultViewSerializer
            if results is not None:
                results_view = result_serializer(
                    results, 
                    many=True, 
                    context={'request': self.context['request']})
                slot_data['results'] = results_view.data
            else:
                slot_data['results'] = None
            result_data_by_slot.append(slot_data)
        return result_data_by_slot

    def _get_slots_in_squad_results(self, slots, event):
        courses = Course.objects.filter(event=event).all()
        courses_overall = courses.count() + 1 if courses else 0
        # сколько результатов у каждого участника
        for slot in slots:
            slot_results = AggregatedCourseResultForSlot.objects.filter(slot=slot).all()
            slot_courses_passed = slot_results.count()
            if slot_courses_passed != courses_overall:
                return False
        return True

    def get_result_status(self, obj):
        event = obj.event
        participants_in_squad = Slot.objects.filter(event=event, squad=obj).all()
        result_status = self._get_slots_in_squad_results(participants_in_squad, event)
        return result_status

    class Meta:
        model = Squad
        exclude = ['event', 'created', 'updated', 'id']
