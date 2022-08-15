from atlima_django.ipsc.models import Weapon
from rest_framework.views import APIView
from django.http import JsonResponse
from atlima_django.sport_events.models import (Team, 
                                               Slot, 
                                               Event, 
                                               Discipline,
                                               Division)
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from atlima_django.users.models import User
from atlima_django.money.models import PromoCode
from django.db.models import Q
from atlima_django.sport_events.models import EventProperty
from atlima_django.ipsc.models import (Squad, 
                                       Course, 
                                       Penalty, 
                                       AggregatedCourseResultForSlot,
                                       CoursePenalty)
from atlima_django.location.models import Country, Region
from atlima_django.money.models import TransactionHistory, OrderItem
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from atlima_django.sport.models import SportAdministrator
from django.db.models.functions import Lower
from django.db.models import CharField
from atlima_django.users.api.serializers import UserSerializer
from atlima_django.ipsc.api.serializers import CourseSerializer
from rest_framework.permissions import IsAuthenticated


# оружие для спортивной стрельбы 
class Weapons(APIView):

    def get(self, request):
        weapons = Weapon.objects.all()
        itemlist = []
        for weapon in weapons:
            item = {}
            item['id'] = weapon.id
            if weapon.image:
                item['logo'] = weapon.image.url
            else:
                item['logo'] = None
            item['title'] = weapon.title
            item['description'] = weapon.description
            itemlist.append(item)
        result = {}
        result['weapons'] = itemlist
        return JsonResponse(result, safe=False, status=200)


# искать админа по региону    
class SearchAdminByRegion(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        data = request.data
        user = request.user
        # profile = AtlimaUser.objects.get(user=user)

        request_user_region = SportAdministrator.objects.get(user=user).region

        CharField.register_lookup(Lower, 'lower')
        serializer = UserSerializer

        try:
            username = data['username']
            region_id = data.get('region_id')
            country_id = data.get('country_id')
            username = username.lower()

            users_in_admin = SportAdministrator.objects.values_list('user', flat=True).distinct()
            
            try:
                region = Region.objects.get(id=region_id)
            except ObjectDoesNotExist:
                region = None

            try:
                country = Country.objects.get(id=country_id)
            except ObjectDoesNotExist:
                country = None

            profile = User.objects.filter(
                Q(first_name__lower__contains=username)
                | 
                Q(last_name__lower__contains=username)
                ).filter(is_active=True).values_list('id', flat=True).distinct()
            
            profile = profile.filter(is_active=True)
            profs = User.objects.filter(id__in=profile, active=True)
            profs = profs.filter(~Q(id__in=users_in_admin))
            profile_region = profs
            
            if country:
                profile_region = profs.filter(country=country)

            users = User.objects.filter(
                id__in=profile_region, 
                active=True).values_list(
                    'user', flat=True
                    ).distinct()
                
            users = User.objects.filter(id__in=users, 
                                        is_active=True)

            if users is not None:
                serialized = serializer(users, many=True)
                return JsonResponse(serialized.data, safe=False)
            else:
                return JsonResponse([], safe=False)

        except KeyError:
            return JsonResponse({"status": False, "errors": {'fields': ['username, region_id is required']}})



class DivisionsAPI(APIView):
    """Выводит все дивизионы"""
    def get(self, request):
        response = {
            1: {"name": 'CLS', "en": 'Classic', "ru":'Классический класс'},
            2: {"name": 'MDF', "en":'Modified', "ru":'Модифицированный класс'},
            3: {"name": 'OPN', "en":'Open', "ru":'Открытый класс'},
            4: {"name": 'STD', "en":'Standard', "ru":'Стандартный класс'},
            5: {"name": 'PRD', "en":'Serial', "ru":'Серийный класс'},
            6: {"name": 'PRDO', "en":'Serial Optic', "ru":'Серийный класс с оптическим прицелом'},
            7: {"name": 'PRDOL', "en":'Serial Optic Light', "ru":'Серийный класс с оптическим прицелом, лёгкий'},
            8: {"name": 'OPNAA', "en":'Action Air Open', "ru":'Открытый класс'},
            9: {"name": 'STDAA', "en":'Action Air Standard', "ru":'Стандартный класс'},
            10: {"name": 'PRDAA', "en":'Action Air Serial', "ru":'Серийный класс'},
            11: {"name": 'REV', "en":'Revolver', "ru":'Револьвер'},
            12: {"name": 'SAO', "en":'Semi-Auto Open', "ru":'Открытый класс'},
            13: {"name": 'MAO', "en":'Manual Auto Open', "ru":'Открытый класс - ручное перезаряжание'},
            14: {"name": 'SAS', "en":'Semi Auto Standard', "ru":'Стандартный класс'},
            15: {"name": 'MAS', "en":'Manual Auto Standard', "ru":'Стандартный класс - ручное перезаряжание'},
            16: {"name": 'PCC', "en":'', "ru":''},
            17: {"name": 'SAOAA', "en":'Action Air Semi-Auto Open', "ru":'Открытый класс'},
            18: {"name": 'MAOAA', "en":'Action Air Manual Auto Open', "ru":'Открытый класс - ручное перезаряжание'},
            19: {"name": 'SASAA', "en":'Action Air Semi Auto Standard', "ru":'Стандартный класс'},
            20: {"name": 'TRI STD', "en":'Standart', "ru":'Стандартный класс'},
            21: {"name": 'TRI OPN', "en":'Open', "ru":'Открытый класс'},
            22: {"name": 'SGMDF', "en":'Modified', "ru":'Модифицированный класс'},
            23: {"name": 'SGOPN', "en":'Open', "ru":'Открытый класс'},
            24: {"name": 'SGPMP', "en":'Pump', "ru":'Помповый класс'},
            25: {"name": 'SGSTD', "en":'Standard', "ru":'Стандартный класс'}
        }

        return JsonResponse(response)



# ЛИСТ ОЖМДАНИЯ ДЛЯ СЛОТОВ
class WaitingListControl(APIView):

    authentication_classes = [TokenAuthentication]

    def put(self, request, slot_id):
        if request.version == "1.0" or request.version is None:
            try:
                slot = Slot.objects.get(id = slot_id)
                slot.squad = None
                slot.save()
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"event_id": "Event not found"}}, status=404)
            return JsonResponse({"status": True})



class SquadAddition(APIView):

    authentication_classes = [TokenAuthentication]

    def post(self, request, event_id):
        data = request.data

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event_id": ["Event not found"]}}, status=404)
        
        squads_amount = Squad.objects.filter(event=event).count()
        
        squad_number = squads_amount + 1
        comment = data.get('comment')
        squad_date = data.get('squad_date')

        new_squad = Squad.objects.create(event=event,
                                        comment=comment,
                                        squad_date=squad_date,
                                        squad_number=squad_number)
        new_squad.save()
    
        return JsonResponse({"status": True, "id": new_squad.id})



# УПРАВЛЕНИЕ СКВОДАМИ
class SquadControl(APIView):

    authentication_classes = [TokenAuthentication]

    def put(self, request, squad_id):
        data = request.data
        comment = data.get('comment')
        date = data.get('squad_date')
        
        
        try:
            squad = Squad.objects.get(id=squad_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"squad_id": ["squad not found"]}})
        
        if comment is not None:
            squad.comment = comment
            squad.save()

        if date is not None:
            squad.squad_date = date
            squad.save()
        
        return JsonResponse({"status": True})


    def delete(self, request, squad_id):
        try:
            squad = Squad.objects.get(id=squad_id)
            n = squad.squad_number
            slots = Slot.objects.filter(squad=squad).all()
            for slot in slots:
                slot.squad = None
                slot.save()
            squad.delete()
            
            reformatted_squads = Squad.objects.filter(squad_number__gt = n).all()
            for s in reformatted_squads:

                s.squad_number -= 1

                slots = Slot.objects.filter(squad=s).values_list('user', flat=True).distinct()
                users_for_sent = User.objects.filter(id__in=slots).all()
                for user_sent in users_for_sent:
                    try:
                        create_system_event_object(user_sent, 'squad_number_changed', {"id": s.event.id,"squad_number": s.squad_number})
                    except:
                        pass

                s.save()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"squad_id": ['squad not found']}}, status=404)
            
        return JsonResponse({"status": True, "message": f"Squad {squad_id} deleted successfully"})


class CourseInEvent(APIView):
    # authentication_classes = [BasicAuthentication, TokenAuthentication]
    # permission_classes = [IsAuthenticated,]
    
    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "event not found"}, status=404)
        serializer = CourseSerializer
        courses = Course.objects.filter(event=event).order_by('course_number')
        if courses.count()>0:
            serialized = CourseSerializer(courses, many=True, context={'request': request})
            data = serialized.data
            return JsonResponse(data, safe=False)
        else:
            return JsonResponse([], safe=False)


class SingleCourseView(APIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request, course_id):
        serializer = CourseSerializer
        courses = Course.objects.filter(id=course_id).first()
        if courses is not None:
            serialized = CourseSerializer(courses, context={'request': request})
            return JsonResponse(serialized.data, safe=False)
        else:
            return JsonResponse({})


class CheckCourseResultsExist(APIView):
    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
            results = AggregatedCourseResultForSlot.objects.filter(course=course).all()
            if results.count() > 0:
                return JsonResponse({"status": True})
            else:
                return JsonResponse({"status": False})
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "course not found"}, status=404)
        
        
        

class TargetView(APIView):
    def get(self, request):
        serializer = TargetTypeSerializer
        targets = TargetType.objects.all()
        serialized = serializer(targets, many=True)
        return JsonResponse(serialized.data, safe=False)


# ВВОД РЕЗУЛЬТАТОВ И ШТРАФОВ 
class PenaltyList(APIView): 

    # authentication_classes = [BasicAuthentication, TokenAuthentication]
    # permission_classes = [IsAuthenticated,]

    def get(self, request):
        if request.version == "1.0" or request.version is None:
            serializer = PenaltyContentSerializer
            penalties = Penalty.objects.all()
            serialized = serializer(penalties, many=True, context={'request': request})
            data = serialized.data
            return JsonResponse(data, safe=False)
        else:
            serializer = PenaltyContentSerializer
            penalties = Penalty.objects.all()
            serialized = serializer(penalties, many=True, context={'request': request})
            data = serialized.data
            return JsonResponse(data, safe=False)


class MatchResultAPI(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, slot_id):
        data = request.data
        referee_user = request.user
        result_type = AggregatedCourseResultForSlot.COURSE_TARGET_RESULT
        
        try:
            # получаем все данные для внесения результатов
            course_id = data['course_id']
            A = data.get('A')
            C = data.get('C')
            D = data.get('D')
            M = data.get('M')
            NS = data.get('NS')
            T = data.get('T')
            penalties = data.get('penalties')
            timestamp = data.get('timestamp')
            client_id = data['client_id']
            deduction = data.get('deduction')
            if A is None and C is None and D is None and M is None and NS is None and T is None and penalties is None:
                return JsonResponse({"status": False, "message": "no results from ACDMNST and penalties provided"}, status=400)
            slot = Slot.objects.get(id = slot_id)
            course = Course.objects.get(id = course_id)
        except KeyError:
            return JsonResponse({"status": False, "message": "required params (slot_id, course_id) not found"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "participant slot or course not found"}, status=404)

        referee_slot = RefereeSlot.objects.filter(user=referee_user, event=slot.event).first()
        if referee_slot is None:
            return JsonResponse({"status": False, "errors": {'referee_slot': ['slot not found']}}, status=404)
        
        unique = AggregatedCourseResultForSlot.objects.filter(Q(client_id=client_id)&Q(timestamp=timestamp)&Q(referee_slot=referee_slot)).first()
        if unique is not None:
            return JsonResponse({"status": False, "id": unique.id})

        new_result = AggregatedCourseResultForSlot.objects.create(slot = slot,
                                                                client_id = client_id,
                                                                course = course,
                                                                result_type = result_type,
                                                                A = A,
                                                                C = C,
                                                                D = D,
                                                                M = M,
                                                                NS = NS,
                                                                T = T,
                                                                deduction = deduction,
                                                                referee_slot=referee_slot,
                                                                timestamp=timestamp,
                                                                active=True)
        event = slot.event
        event.has_results = True
        event.registration_opened = False
        event.save()
        new_result.save()
        
        if penalties is not None:
            penalty_array_size = len(penalties)

        if penalties is not None and penalty_array_size > 0:
            for penalty in penalties:
                try:
                    penalty_id = penalty['penalty_id']
                    penalty_instance = Penalty.objects.filter(id=penalty_id).first()
                    amount = penalty['amount']
                    new_penalty = CoursePenalty.objects.create(aggregated_result=new_result,
                                                            penalty=penalty_instance,
                                                            amount=amount,
                                                            active=True)
                    new_penalty.save()
                except KeyError:
                    pass
        
        return JsonResponse({'status': True, 'id': new_result.id})


class MatchResultUpdateAPI(APIView):
    
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request, result_id):
        try:
            match_result = AggregatedCourseResultForSlot.objects.get(id=result_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "no result found"}, status=404)

        serializer = AggregatedCourseResultForSlotSerializer
        serialized = serializer(match_result, context={"request": request})

        return JsonResponse(serialized.data, safe=False)

    def put(self, request, result_id):
        """добавление фото в результаты"""
        try:
            match_result = AggregatedCourseResultForSlot.objects.get(id=result_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "no result found"}, status=404)
        
        try:
            data = request.data['photo']
        except KeyError:
            return JsonResponse({"status": False, "message": "no photo provided"}, status=400)

        match_result.photo = data
        match_result.save()
        return JsonResponse({"status": True})

    def delete(self, request, result_id):
        try:
            result = AggregatedCourseResultForSlot.objects.get(id=result_id)
            result.active = False
            result.delete_timestamp = datetime.datetime.now()
            result.save()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "no event found"}, status=404)
        return JsonResponse({"status": True})


class PenaltyControl(APIView):
    """Поиск результата и удаление штрафа из него"""
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def delete(self, request, result_id, penalty_id):
        try:
            result = AggregatedCourseResultForSlot.objects.get(id=result_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "result not found"}, status=404)
        try:
            penalty = Penalty.objects.get(id=penalty_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "penalty not found"}, status=404)

        data = request.data
        amount = data['amount']

        try:
            amount = int(amount)
        except ValueError:
            return JsonResponse({"status": False, "errors": {"amount": "amount must be int"}}, status=400)

        if amount < 0:
            return JsonResponse({"status": False, "errors": {"amount": "amount cant be < 0, bad boy"}}, status=400)

        course_penalty = CoursePenalty.objects.get(aggregated_result=result, penalty=penalty, active=True)
        course_penalty.amount = amount
        course_penalty.save()
        return JsonResponse({"status": True})



class DisqualificationCancellation(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def delete(self, request, dq_id):
        try:
            result = AggregatedCourseResultForSlot.objects.get(id=dq_id)
            if result.result_type in [AggregatedCourseResultForSlot.DISQUALIFICATION, AggregatedCourseResultForSlot.DNS]:
                result.active = False
                result.delete_timestamp = datetime.now()
                result.save()
            else:
                return JsonResponse({"status": False, "message": "It is not disqualification!"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "DNS/DQ marks not found"}, status=404)
        
        return JsonResponse({"status": True})


class DisqualificationPhoto(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def put(self, request, dq_id):
        """добавление фото в результат"""
        try:
            result = AggregatedCourseResultForSlot.objects.get(id=dq_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "no disqualification found"}, status=404)
        
        try:
            data = request.data['photo']
        except KeyError:
            return JsonResponse({"status": False, "message": "no photo provided"}, status=400)

        result.photo = data
        result.save()
        return JsonResponse({"status": True})


class DisqualificationRuleClauses(APIView):

    def get(self, request):
        serializer = DisqualificationReasonSerializer
        disqualification_reasons = DisqualificationReason.objects.all()
        serialized = serializer(disqualification_reasons, many=True, context={'request': request})
        data = serialized.data
        return JsonResponse(data, safe=False)



#  ПОДСИСТЕМА УПРАВЛЕНИЯ ДИСКВАЛИФИКАЦИЕЙ
class DisqualificationInterface(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, slot_id):
        data = request.data

        referee_user = request.user
        try:
            cancellation = data['cancellation']
            client_id = data['client_id']
            reason_id = data.get('reason_id')
            slot = Slot.objects.get(id=slot_id)
            if reason_id is not None:
                cancel_reason = DisqualificationReason.objects.get(id=reason_id)
            else:
                cancel_reason = None
            timestamp = data['timestamp']
        except KeyError as ke:
            error = str(ke)
            return JsonResponse({"status": False, "message": f"{error}"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "slot not found"}, status=404)

        referee_slot = RefereeSlot.objects.filter(user=referee_user, event=slot.event).first()
        slot_results = AggregatedCourseResultForSlot.objects.filter(Q(result_type=AggregatedCourseResultForSlot.COURSE_TARGET_RESULT)&Q(slot=slot)&Q(active=True)).all()
        slot_results_amount = slot_results.count()

        # если у участника есть результаты, нельзя отменить участие с отметкой "не стартовал"
        if slot_results_amount > 0:
            if cancellation == AggregatedCourseResultForSlot.DNS:
                return JsonResponse({"status": False, "message": "this participant has results!"}, status=400)

        # unique = AggregatedCourseResultForSlot.objects.filter(result_type=AggregatedCourseResultForSlot.DISQUALIFICATION, slot=slot, timestamp=timestamp, referee_slot=referee_slot).first()
        unique = AggregatedCourseResultForSlot.objects.filter(Q(client_id=client_id)&Q(timestamp=timestamp)&Q(referee_slot=referee_slot)).first()
        if unique is not None:
            return JsonResponse({"status": False, "message": unique.id})
        
        new_cancellation = AggregatedCourseResultForSlot.objects.create(result_type=AggregatedCourseResultForSlot.DISQUALIFICATION,
                                                                        slot=slot,
                                                                        client_id = client_id,
                                                                        cancellation=cancellation,
                                                                        cancel_reason = cancel_reason,
                                                                        referee_slot=referee_slot,
                                                                        timestamp=timestamp)
        new_cancellation.save()

        event = slot.event
        event.has_results = True
        event.registration_opened = False
        event.save()

        return JsonResponse({"status": True, "id": new_cancellation.id})
    
    
# УПРАВЛЕНИЕ КОМАНДАМИ (КОМАНДА ЯВЛЯЕТСЯ ЧАСТЬЮ СЛОТА)

class TeamAPI(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request, event_id):
        """Получение списка команд в событии"""
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "event not found"}, status=404)

        teams = Team.objects.filter(event=event).all()
        serializer = TeamSerializer
        count = teams.count()
        # список команд
        filtered = []
        if count > 0:
            # отфильтровать только команды, в которых меньше 4-х участников
            for team in teams:
                slots_in_team = Slot.objects.filter(team=team).all()
                if slots_in_team.count() < 4:
                    filtered.append(team)

            serialized = serializer(filtered, many=True)
            return JsonResponse(serialized.data, safe=False)
        else:
            return JsonResponse({})

    def post(self, request, event_id):
        """Проверка команды на существование"""
        data = request.data
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "event not found"}, status=404)

        try:
            team = data['team']
            team_instance = Team.objects.get(title=team)
        except KeyError:
            return JsonResponse({"status": False, "message": "team is required"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "team not found"})
        
        return JsonResponse({"status": True})


# АВТОСКВОДИНГ
class AutoSquading(APIView):
    def post(self, request, event_id):
        try:
            event = Event.objects.get(id = event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event_id": ['event not found']}}, status=400)
        # получим максимальное количество человек в скводе
        try:
            properties = EventProperty.objects.get(event=event)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Properties not found for this event"}, status=400)
        max_users_in_squad = properties.shooters_in_squad

        # получим все скводы, которые не заблокированы
        squads = Squad.objects.filter(event=event, is_blocked=False).order_by('squad_number')

        for squad in squads:
            squad_slots = Slot.objects.filter(squad=squad).count()
            
            if squad_slots < max_users_in_squad:
                need_to_update = max_users_in_squad - squad_slots
                # получим первый слот из листа ожидания
                waiting_list_slot_top = Slot.objects.filter(Q(event=event)&Q(squad__isnull=True)&Q(user__isnull=False)&Q(paid=True)&Q(active=True)).order_by('updated')[:need_to_update]
                # присвоим сквод
                if waiting_list_slot_top is not None:
                    for slot_to_update in waiting_list_slot_top:
                        slot_to_update.squad = squad
                        slot_to_update.save()
            else:
                continue

        return JsonResponse({"status": True})



class DisciplinesAPI(APIView):
    
    def get(self, request):
        """Вернуть все дисциплины в системе"""
        serializer = DisciplineSerializer
        disciplines = Discipline.objects.filter(active=True).all()
        serialized = serializer(disciplines, many=True, context={"request": request})
        return JsonResponse(serialized.data, safe=False)



class AssignParticipantToSquadById(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication,]
    permission_classes = [
        IsAuthenticated,
    ]

    def put(self, request, squad_id):
        try: 
            squad = Squad.objects.get(id=squad_id)
        except ObjectDoesNotExist:
            squad = None

        if squad is not None:
            event = squad.event

            properties = EventProperty.objects.get(event=event)
            max_shooters_in_squad = properties.shooters_in_squad
            current_shooters_in_squad = Slot.objects.filter(squad=squad).count()
        
            user = request.user
            try:
                slot = Slot.objects.get(event=event, 
                                        user=user,
                                        active=True)
            except ObjectDoesNotExist:
                slot = None

            if slot is not None:
                if current_shooters_in_squad + 1 > max_shooters_in_squad:
                    try:
                        event_admin = EventAdministration.objects.get(user=user, event=event)
                        if event_admin.is_director is True:
                            slot.squad = squad
                            slot.save()                
                    except ObjectDoesNotExist:
                        return JsonResponse({"status": False, "message": "only director can assign user to full-packed squad"}, status=400)
                else:
                    slot.squad = squad
                    slot.save()                
            else:
                return JsonResponse({"status": False, 
                                    "errors": {"slot": "slot for user not found"}}, 
                                    status=404)
        else:
            return JsonResponse({"status": False, 
                                "errors": {"squad_id": ["squad not found"]}}, 
                                status=404)

        return JsonResponse({"status": True})
    
    
# экран администрирования администраторов события
class EventAdministrationScreen(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        event_administration = EventAdministration.objects.all()

        # выбрать все мероприятия в админке без повторений
        events_in_admin = EventAdministration.objects.values_list('event', flat=True).distinct()
        language = self.get_language(request=request)
        items = []

        for event in events_in_admin:
            item = {}
            related_event = Event.objects.get(id=event)
            list_of_users_for_event = Event.objects.filter(event=related_event).first()

            # указываем ID ивента
            item['event_id'] = related_event.id
            related_title = related_event.title
            if related_title:
                item['event_title'] = related_title.title
                item['description'] = related_title.description

            user_list = []
            # получаем все нужные данные для отображения списка пользователей-админов
            for user in list_of_users_for_event:
                user_item = {}
                user_item['id'] = user.id
                user_item['first_name'] = user.first_name
                user_item['last_name'] = user.last_name

                user_list.append(user_item)
            
            item['admins'] = user_list
            items.append(item)
        
        result = {}
        result['event-admins'] = items
        return JsonResponse(result, safe=False)