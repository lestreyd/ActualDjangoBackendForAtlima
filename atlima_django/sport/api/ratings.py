from .utils import get_valid_system_slots
from rest_framework.views import APIView
from constance import config
from atlima_django.users.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from atlima_django.sport.api.serializers import SportSerializer
from atlima_django.sport_events.api.serializers import EventMenuSerializer
from atlima_django.sport.api.utils import get_my_rank
from models import Sport, Discipline
from rest_framework import generics
from itertools import islice
from atlima_django.ipsc.models import DisciplineSerializer
from atlima_django.sport.api.serializers import SportSerializer



class RatingDashboard(APIView):
    """Класс, описывающий рейтинг спорстмена в конкретный
    момент времени на конкретном событии (указан на слоте)
    Здесь НЕ выводится твой ранг, выводятся только показатели
    по дисциплине и показатели по спорту в целом"""
    def _get_sport_rating(self, sport, user):
        slots = get_valid_system_slots()
        slots = slots.filter(
            event__sport_type=sport, 
            user=user).all()
        sport_rating_overall = 0
        for overall_slot in slots:
            sport_rating_overall += overall_slot.rating_increase
        rating = round(config.INITIAL_RATING + sport_rating_overall)
        return rating

    def get(self, request):
        user = request.user
        sports = Sport.objects.all()
        ratings = []
        result = {}

        # если пользователь передан в get параметрах
        # то берём его результаты для обсчёта
        user_id = request.GET.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, 
                "errors": {"user": ['not found']}}, status=404)

        sport_serializer = SportSerializer
        discipline_serializer = DisciplineSerializer

        for sport in sports:
            slots = get_valid_system_slots().filter(user=user)
            slot_counter = slots.count()
            if slot_counter >= 1:
                last_slot = slots.latest('created')
                sport_rating_overall = 0
                for overall_slot in slots:
                    sport_rating_overall += overall_slot.rating_increase             
                rating = self._get_sport_rating(sport, user)
                result['sport'] = sport_serializer(sport, context={'request': request}).data
                result['events'] = slot_counter
                result['change'] = round(sport_rating_overall)
                result['rating'] = rating
                result['changes'] = []
                disciplines = slots.values_list("discipline", flat=True).distinct()
                for discipline in disciplines:
                    last_slot = slots.filter(discipline=discipline).order_by('-created').first()
                    discipline = Discipline.objects.get(id=discipline)
                    discipline_rating_history = {}
                    slots_in_disciplines = slots.filter(discipline=discipline).all()
                    slots_in_disciplines_count = slots_in_disciplines.count()
                    discipline_rating_history['events'] = slots_in_disciplines_count
                    aggregated_discipline_change = 0
                    
                    aggregated_discipline_points = last_slot.initial_rating + last_slot.rating_increase
                    
                    for result_slot in slots_in_disciplines:
                        aggregated_discipline_change += result_slot.rating_increase
                    
                    discipline_serialized = discipline_serializer(discipline, context={'request': request}).data
                    discipline_rating_history['discipline'] = discipline_serialized
                    discipline_rating_history['rating_change'] = round(aggregated_discipline_change)
                    discipline_rating_history['points_change'] = int(aggregated_discipline_points)
                    result['changes'].append(discipline_rating_history)
            if len(result) == 0:
                return JsonResponse([], safe=False)
            ratings.append(result)
        return JsonResponse(ratings, safe=False)



class SportRatingDashboard(APIView):
    """Дашборд рейтинга по виду спорта"""
    
    def _get_sport_rating(self, sport, user):
        slots = get_valid_system_slots()
        slots = slots.filter(event__sport_type=sport, user=user).all()
        sport_rating_overall = 0
        for overall_slot in slots:
            sport_rating_overall += overall_slot.rating_increase
        rating = config.INITIAL_RATING + sport_rating_overall
        return round(rating)

    def get(self, request):

        user = request.user
        valid_slots = get_valid_system_slots()

        user_id = request.GET.get('user_id', None)
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"user": ["not found"]}}, status=404)

        sport_id = request.GET.get('sport_id', None)
        check = Sport.objects.filter(id=sport_id).first()
        if check is None:
            return JsonResponse({"status": False, "errors": {"sport": ["not found"]}}, status=404)

        ratings = []
        result = {}
        sport_serializer = SportSerializer
        event_serializer = EventMenuSerializer
        slots = valid_slots.filter(event__sport_type__id=sport_id, user=user).all().order_by('-event__start_event_date')
        slot_counter = slots.count()

        if slot_counter >= 1:
            sport = Sport.objects.get(id=sport_id)
            rating = self._get_sport_rating(sport, user)
            result['sport'] = sport_serializer(sport, context={'request': request}).data
            result['events'] = slot_counter
            result['rating'] = rating
            # result['world_rank'] = self._get_world_rank(sport, user.id)
            result['world_rank'] = get_my_rank(
                sport=sport, 
                target_user=user.id, 
                scope="world",
                discipline=None)
            result['country_rank'] = get_my_rank(
                sport=sport, 
                target_user=user.id, 
                scope="country",
                discipline=None,)
            result['region_rank'] = get_my_rank(
                sport=sport, 
                target_user=user.id, 
                scope="region",
                discipline=None)

            last_5_result = 0
            last_5_slot_results = slots.order_by('-created')[:5]
            for slot_result in last_5_slot_results:
                last_5_result += slot_result.rating_increase
            result['last_5_changes'] = round(last_5_result)
            result['changes'] = []
            prev_rate = 0

            for event_marker in slots:
                change = {}
                if prev_rate == 0:
                    change['absolute_rate'] = config.INITIAL_RATING + event_marker.rating_increase
                    prev_rate = config.INITIAL_RATING + event_marker.rating_increase
                else:
                    change['absolute_rate'] = event_marker.rating_increase + prev_rate
                    prev_rate = event_marker.rating_increase + prev_rate
                change['event'] = event_serializer(event_marker.event, context={'request': request}).data
                change['amount'] = event_marker.rating_increase
                result['changes'].append(change)

        ratings.append(result)

        return JsonResponse(ratings, safe=False)


class DisciplineRatingDashboard(APIView):
    """Дащборд рейтинга для вывода по
    дисциплинам"""

    def _get_discipline_rating(self, discipline, user):
        discipline_rating = 0
        slots = get_valid_system_slots()
        last_slot = slots.filter(
            user=user, 
            discipline=discipline).order_by('-created').first()
        if last_slot:
            discipline_rating = last_slot.initial_rating + last_slot.rating_increase
            return discipline_rating
        return 0

    def get(self, request, sport_id, discipline_id):
        """Метод для расчёта дашборды по конкретной дисциплине"""
        user = request.user
        user_id = request.GET.get('user_id')
        if user_id is not None:
            try:
                user = User.objects.get(id=user_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"user": ["not found"]}}, status=404)
        try:
            discipline = Discipline.objects.get(id=discipline_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"discipline_id": ["no such discipline"]}}, status=404)
        ratings = []
        result = {}

        sport_serializer = SportSerializer
        event_serializer = EventMenuSerializer
        discipline_serializer = DisciplineSerializer

        slots = get_valid_system_slots()
        slots = slots.filter(
            event__sport_type__id=sport_id, 
            user=user, 
            discipline=discipline
            ).all().order_by('-event__start_event_date')

        if slots is not None:
            slot_counter = slots.count()
        else:
            slot_counter = 0

        if slot_counter >= 1:
            sport = Sport.objects.get(id=sport_id)
            last_slot = slots.filter(discipline=discipline).order_by('-created').first()
            discipline_rating_history = {}
            slots_in_disciplines = slots.filter(discipline=discipline).all()[:5]
            aggregated_discipline_change = 0
            aggregated_discipline_points = last_slot.initial_rating + last_slot.rating_increase
            
            for result_slot in slots_in_disciplines:
                aggregated_discipline_change += result_slot.rating_increase

            discipline_serialized = discipline_serializer(discipline, context={'request': request}).data
            discipline_rating_history['discipline'] = discipline_serialized
            discipline_rating_history['rating_change'] = round(aggregated_discipline_change)
            discipline_rating_history['points_change'] = int(aggregated_discipline_points)
            
            # result['changes'].append(discipline_rating_history)
            result['sport'] = sport_serializer(sport, context={'request': request}).data
            result['events'] = slot_counter
            result['rating'] = round(aggregated_discipline_points)

            result['world_rank'] = get_my_rank(
                sport=sport, 
                target_user=user_id, 
                discipline=discipline, 
                scope="world")

            result['country_rank'] = get_my_rank(
                sport=sport, 
                target_user=user.id, 
                discipline=discipline, 
                scope="country")

            result['region_rank'] = get_my_rank(
                sport=sport, 
                target_user=user.id, 
                discipline=discipline, 
                scope="region")

            result['last_5_changes'] = round(aggregated_discipline_change)
            result['changes'] = []
            
            prev_rate = 0
            for event_marker in slots:
                change = {}
                change['event'] = event_serializer(event_marker.event, context={'request': request}).data
                change['amount'] = event_marker.rating_increase
                result['changes'].append(change)

                if prev_rate == 0:
                    change['absolute_rate'] = config.INITIAL_RATING + event_marker.rating_increase
                    prev_rate = config.INITIAL_RATING + event_marker.rating_increase
                else:
                    change['absolute_rate'] = event_marker.rating_increase + prev_rate
                    prev_rate = event_marker.rating_increase + prev_rate
        if len(result) > 0:
            ratings.append(result)
        return JsonResponse(ratings, safe=False)


class DashboardOverall(generics.ListAPIView):
    """Дашборд для рейтинга, выводит показатели
    по спорту/дисциплине и выводит ранг пользователя"""

    def _get_sport_rating(self, sport, user):
        slots = get_valid_system_slots()
        slots = slots.filter(event__sport_type=sport, user=user).all()
        sport_rating_overall = 0
        for overall_slot in slots:
            sport_rating_overall += overall_slot.rating_increase
        rating = config.INITIAL_RATING + sport_rating_overall
        return round(rating)

    def _get_discipline_rating(self, discipline, user):
        discipline_rating = 0
        slots = get_valid_system_slots()
        last_slot = slots.filter(user=user, discipline=discipline).order_by('-event__start_event_date').first()
        if last_slot:
            discipline_rating = last_slot.initial_rating + last_slot.rating_increase
            return round(discipline_rating)
        return 0

    def get(self, request):

        user = request.user
        discipline_id = request.GET.get('discipline_id', None)
        sport_id = request.GET.get('sport_id', None)
        region_splice = request.GET.get('splice', None)
        cursor = request.GET.get('cursor', None)
        direction = request.GET.get('direction', None)
        limit = request.GET.get('limit', None)

        if sport_id is None:
            return JsonResponse({"status": False, 
            "errors": {"sport_id": ["field is required"]}}, 
            status=400)
        
        result = []
        sport = Sport.objects.get(id=sport_id)
        valid_slots = get_valid_system_slots()

        if discipline_id is not None:
            
            discipline = Discipline.objects.get(id=discipline_id)
            slots = valid_slots.filter(event__sport_type=sport, 
            discipline=discipline
            ).order_by('-event__start_event_date')

            users = slots.values_list('user', flat=True).distinct()
            for user in users:
                if region_splice:
                    if region_splice.lower() == 'world':
                        rank = get_my_rank(
                            sport=sport,
                            target_user=user.id,
                            discipline=discipline,
                            scope="world")
                    elif region_splice.lower() == 'country':
                        rank = get_my_rank(
                            sport=sport, 
                            target_user=user.id, 
                            discipline=discipline,
                            scope="country")
                    elif region_splice.lower() == 'region':
                        rank = get_my_rank(
                            sport=sport, 
                            target_user=user.id, 
                            discipline=discipline,
                            scope="region")
                else:
                    rank = self._get_discipline_rating(discipline, user)
                
                user_record = {}
                user_record['id'] = user
                user_instance = User.objects.get(id=user)
                user_record['username'] = f"{user_instance.first_name} {user_instance.last_name}"

                profile = User.objects.filter(user=user_instance).first()
                if profile:
                    if profile.country:
                        user_record['country_code'] = profile.country.alpha2
                else:
                    user_record['country_code'] = None

                user_record['rating'] = rank
                result.append(user_record)
        else:
            slots = valid_slots.filter(event__sport_type=sport).order_by('-event__start_event_date')
            users = slots.values_list('user', flat=True).distinct()
            users = set(users)

            for user in users:
                user_record = {}
                if region_splice:
                    if region_splice.lower() == 'world':
                        rating = get_my_rank(sport=sport, 
                                            target_user=user.id,
                                            discipline=None,
                                            scope="world")
                    elif region_splice.lower() == 'country':
                        rating = get_my_rank(sport=sport, 
                                            target_user=user,
                                            discipline=None,
                                            scope="country")
                    elif region_splice.lower() == 'region':
                        rating = get_my_rank(sport=sport,
                                            target_user=user,
                                            discipline=None,
                                            scope="region")
                else:
                    rating = self._get_sport_rating(sport, user)
                user_record['id'] = user
                user_instance = User.objects.get(id=user)
                user_record['username'] = f"{user_instance.first_name} {user_instance.last_name}"
                profile = User.objects.filter(id=user_instance.id).first()
                if profile:
                    if profile.country:
                        user_record['country_code'] = profile.country.alpha2
                else:
                    user_record['country_code'] = None
                user_record['rating'] = rating
                
                result.append(user_record)

        sorted_by_rank_set = sorted(result, key=lambda d: d['rating'], reverse=True)
    
        for idx, item in enumerate(sorted_by_rank_set):
            item['order'] = idx
        
        default_pagination_limit = 10
        page_limit = 0
        if limit:
            page_limit = int(limit)
        else:
            page_limit = default_pagination_limit
        start_idx = 0
        end_idx = 0

        if cursor is not None:
            try:
                cursor = int(cursor)
            except ValueError:
                cursor = None
        else:
            cursor = None
        
        if direction is not None:
            if direction.lower() not in ('asc', 'desc'):
                direction=None
                
        if cursor is None and direction is None:
            try:
                my_idx = next(index for (index, d) in enumerate(sorted_by_rank_set) if d['id']==request.user.id)
                start_idx = my_idx
                end_idx = my_idx + page_limit if my_idx + page_limit < len(sorted_by_rank_set) - 1 else len(sorted_by_rank_set)
                paginated_slice = islice(sorted_by_rank_set, start_idx, end_idx)
                sorted_by_rank = []
                for result in paginated_slice: 
                    sorted_by_rank.append(result)
                if end_idx == len(sorted_by_rank_set):
                    end_idx = None 
            except StopIteration:
                paginated_slice = islice(sorted_by_rank_set, 0, page_limit)
                start_idx = 0
                sorted_by_rank = []
                for result in paginated_slice: sorted_by_rank.append(result)
                end_idx = page_limit if page_limit <= len(sorted_by_rank) - 1 else None
        elif direction is not None and cursor is not None:
            if direction.lower() == 'desc':
                start_idx = cursor - page_limit - 1
                if start_idx < 0: start_idx = 0
                end_idx = cursor
                sorted_by_rank = []
                paginated_slice = islice(sorted_by_rank_set, start_idx, end_idx)
                for result in paginated_slice: sorted_by_rank.append(result)
                if start_idx == 0: 
                    start_idx = None
                else:
                    start_idx  -= 1
                if cursor > len(sorted_by_rank_set) - 1: 
                    end_idx = None
            elif direction.lower() == 'asc':
                my_idx = cursor
                if my_idx > len(sorted_by_rank_set) - 1: my_idx = len(sorted_by_rank_set) - 1
                end_idx = my_idx + page_limit - 1 if my_idx + page_limit - 1 < len(sorted_by_rank_set) - 1 else len(sorted_by_rank_set) - 1
                sorted_by_rank = []            
                if my_idx == 0:
                    start_idx = None
                else:
                    start_idx = my_idx - 1
                paginated_slice = islice(sorted_by_rank_set, my_idx, end_idx + 1)
                for result in paginated_slice: sorted_by_rank.append(result)

                if end_idx == len(sorted_by_rank_set) - 1: 
                    end_idx = None
                else:
                    end_idx += 1
        
        return JsonResponse({"users": sorted_by_rank, 
                            "pagination": {"cursor": {"desc": start_idx, "asc": end_idx}}}, safe=False)