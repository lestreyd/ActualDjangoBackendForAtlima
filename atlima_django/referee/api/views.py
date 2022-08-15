from rest_framework.views import APIView
from atlima_django.referee.models import RefereeSlot
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.http import json
from atlima_django.referee.models import EventRefereeInvite
from atlima_django.referee.api.serializers import RefereeInviteSerializer
from atlima_django.sport_events.models import Event, EventAdministration
from django.db.models.functions import F
from django.http import JsonResponse
from atlima_django.users.models import User
from atlima_django.users.api.serializers import UserSerializer
from transliterate import translit
from atlima_django.qualification.models import OfficialQualification
from atlima_django.ipsc.api.serializers import (TargetResultViewSerializer,
                                                AggregatedCourseResultForSlot,
                                                )
from django.db.models import Q
from django.db.models.functions import F
from atlima_django.ipsc.models import Squad
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from atlima_django.sport_events.models import EventAdministration, Slot, EventProperty
from atlima_django.qualification.models import OfficialQualification
from atlima_django.ipsc.models import Course, Discipline, Target, TargetType, TargetSet, Weapon
from django.db.models.functions import Lower
from atlima_django.referee.api.serializers import RefereeSlotSerializer
from atlima_django.ipsc.api.serializers import (AggregatedCourseResultForSlotSerializer, DisciplineSerializer, SlotSerializer)
from django.db.models import CharField
from atlima_django.referee.api.serializers import RefereeSlotSerializer
from atlima_django.ipsc.models import Target, TargetSet, RefereeSquadSerializer, RGSerializer
from atlima_django.notifications.models import Notification, NotificationTemplate
from atlima_django.referee.models import RefereeGrade
from atlima_django.referee.api.serializers import RGSerializer
from datetime import datetime
from atlima_django.sport_events.models import UserInterestedIn
from django.conf import settings
from atlima_django.ipsc.api.serializers import DisqualificationViewSerializer, DisciplineSerializer, GuncheckViewSerializer
from atlima_django.qualification.api.serializers import OfficialQualificationSerializer
from atlima_django.sport_events.api.serializers import EventMenuSerializer, EventEVSKStatus
from atlima_django.common.api.utils import create_system_event_object

from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

from atlima_django.sport.models import Sport

from reportlab.lib.styles import (ParagraphStyle, getSampleStyleSheet)

style = getSampleStyleSheet()

# ВЫСЛАТЬ ПРИГЛОС СУЛЬЕ НА СОБЫТИЕ
class RefereeInvitesByEventId(APIView):

    def get (self, request, event_id):
        serializer = RefereeInviteSerializer
        result = {}
        
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"event": ["not found"]}}, status=404)

        # сначала отфильтруем список всех, кто уже подтверждён как судья на мероприятие
        approved = EventRefereeInvite.objects.filter(Q(event=event)&(Q(status=EventRefereeInvite.APPROVED)|Q(status=EventRefereeInvite.MODERATED))).all()
        serialized = serializer(approved, many=True)
        result['approved'] = serialized.data

        # получим список всех, кто заявлялся сам как судья на мероприятие
        requested = EventRefereeInvite.objects.filter(event=event).filter(Q(user=F('created_by'))&(~Q(status=EventRefereeInvite.DISMISSED)&~Q(status=EventRefereeInvite.APPROVED)&~Q(status=EventRefereeInvite.MODERATED))).all()
        serialized = serializer(requested, many=True)
        result['requested'] = serialized.data

        # и список тех, кого заявлял Главный судья или Заместитель главного судьи
        invited = EventRefereeInvite.objects.filter(~Q(user=F('created_by'))&Q(event=event)&Q (status=EventRefereeInvite.WAITING)).all()
        serialized = serializer(invited, many=True)
        result['invited'] = serialized.data
        return JsonResponse(result, safe=False)



# ПОИСК СУДЬИ (С ПОДТВЕРЖДЁННОЙ ОФИЦИАЛЬНОЙ КВАЛОЙ)
class SearchRefereeByName(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        data = request.data
        CharField.register_lookup(Lower, 'lower')
        serializer = UserSerializer

        try:
            username = data['username']
            event_id = data.get('event_id')
            event = None
            if event_id:
                try:    
                    event = Event.objects.get(id=event_id)
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "errors": {"event_id": ['event not found']}}, status=400)

            users_in_match = RefereeSlot.objects.filter(event=event).values_list('user', flat=True).distinct()
            director = EventAdministration.objects.filter(event=event, is_director=True).first()
            if director:
                director = director.user.id

            username = username.lower() 
            translated = translit(username, language_code='ru', reversed=True)

            users = User.objects.filter(
                (
                Q(first_name__lower__contains=username)|Q(first_name__lower__contains=translated)|Q(last_name__lower__contains=translated)|Q(last_name__lower__contains=username)
                )
                ).filter(~Q(id=self.request.user.id)&~Q(id=director)).all()

            # if users_in_match:
            #     users = users.filter(~Q(id__in=users_in_match))
            

            referee_qualified_users = OfficialQualification.objects.filter(qualification=2, approved=True).values_list('user', flat=True).distinct()

            users_filtered = users.filter(id__in=referee_qualified_users)
            
            if users_filtered is not None:
                serialized = serializer(users_filtered, many=True)
                return JsonResponse(serialized.data, safe=False)
            else:
                return JsonResponse([], safe=False)
        except KeyError:
            return JsonResponse({"status": False, "errors": {'username': ['username is required']}})


# ПОДСИСТЕМА ПРОСМОТРА СУДЕЙ
class RefereeViewAPI(APIView):
    """просмотр результатов по скводам/слотам"""
    # authentication_classes = [BasicAuthentication, TokenAuthentication]
    # permission_classes = [IsAuthenticated,]

    def _get_slot_results(self, request, slot):
        serializer = TargetResultViewSerializer
        slot_results = AggregatedCourseResultForSlot.objects.filter(
            slot = slot,
            result_type = AggregatedCourseResultForSlot.COURSE_TARGET_RESULT,
            active = True
        ).all()
        serialized = serialized(slot_results, context={"request": request})
        results = serialized.data
        return results

    def _get_squads(self, request, event):
        # TODO разнести на сериализаторы
        # слота для судейства и сквода для судейства
        squads = Squad.objects.filter(event=event).all()
        serializer = AggregatedCourseResultForSlotSerializer
        slot_serializer = SlotSerializer
        squad_serializer = RefereeSquadSerializer
        squad_disposition = []
        if event.imported is False:
            for squad in squads:
                serialized_squad = squad_serializer(
                    squad
                )
                squad_data = serialized_squad.data
                slots_in_squad = Slot.objects.filter(
                    squad=squad, 
                    paid=True, 
                    active=True).all()
                included_slots= []
                for slot in slots_in_squad:
                
                    serialized_slot = slot_serializer(
                            slot,
                            context={"request": request})
                    slot_data = serialized_slot.data
                    # собираем всю информацию по дисквалификациям
                    disqualification = AggregatedCourseResultForSlot.objects.filter(
                        slot = slot_data['id'],
                        result_type=AggregatedCourseResultForSlot.DISQUALIFICATION,
                        active=True
                    ).first()         
                    if disqualification:
                        disqualification_serializer = DisqualificationViewSerializer
                        disqualification_serialized = disqualification_serializer(disqualification)
                        slot_data['DQ'] = disqualification_serialized.data
                    else:
                        slot_data['DQ'] = None

                    # собираем ганчек
                    guncheck = AggregatedCourseResultForSlot.objects.filter(
                        slot=slot_data['id'],
                        result_type=AggregatedCourseResultForSlot.GUNCHECK,
                        active=True
                    ).order_by('created').first()

                    if guncheck:
                        guncheck_serializer = GuncheckViewSerializer
                        guncheck_serialized = guncheck_serializer(guncheck)
                        slot_data['guncheck'] = guncheck_serialized.data
                    else:
                        slot_data['guncheck'] = None
                    # получаем все посчитанные результаты

                    slots_result_count = AggregatedCourseResultForSlot.objects.filter(
                        slot=slot,
                        active=True).count()
                    target_result_serializer = TargetResultViewSerializer
                    details = AggregatedCourseResultForSlot.objects.filter(
                        slot = slot,
                        active=True,
                        result_type=AggregatedCourseResultForSlot.COURSE_TARGET_RESULT
                    ).order_by('created').all()
                    results = target_result_serializer(details, many=True, 
                                                        context={'request': request}
                                                        ).data
                    slot_data['results'] = results
                    included_slots.append(slot_data)

                squad_data['slots'] = included_slots
                courses = Course.objects.filter(event=squad.event).count()
                squad_data['courses_overall'] = courses
                
                courses_passed = AggregatedCourseResultForSlot.objects.filter(
                    result_type = AggregatedCourseResultForSlot.COURSE_TARGET_RESULT,
                    active=True,
                    course__event=event,
                    slot__squad=squad
                ).count()
                
                squad_data['courses_passed'] = courses_passed
                if courses_passed == courses:
                    squad_data['result_status'] = True
                else:
                    squad_data['result_status'] = False
                squad_disposition.append(squad_data)
            return squad_disposition
        
    def get(self, request, event_id):
        """функция для получения результатов по скводам от лица судьи"""
        try:
            event=Event.objects.get(id=event_id)
        except Exception:
            return JsonResponse({"status": False, "errors": {"event": ['not found']}}, status=400)
        squads = self._get_squads(request=request, event=event)
        return JsonResponse(squads, safe=False)
    

# ГЕНЕРАЦИЯ PDF протокола
class GeneratePDFProtocol(APIView):
    """АПИ для генерации протоколов матчей"""
    @staticmethod
    def _get_division_name(division):
        if division == 1:
            division = 'классический класс'
        elif division == 2:
            division = 'модифицированный класс'
        elif division == 3:
            division = 'открытый класс'
        elif division == 4:
            division = 'стандартный класс'
        if division == 5:
            division = 'серийный класс'
        elif division == 6:
            division = 'серийный оптический класс'
        elif division == 7:
            division = 'серийный оптический облегчённый класс'
        elif division == 8:
            division = 'револьвер'
        elif division == 9:
            division = 'открытый'
        elif division == 10:
            division = 'стандартный'
        elif division == 11:
            division = 'открытый с ручным перезаряжанием'
        elif division == 12:
            division = 'стандартный с ручным перезаряжанием'
        elif division == 13:
            division = 'помповое ружьё'
        elif division == 14:
            division = 'карабин пистолетного калибра'
        elif division == 15:
            division = 'с рычаговым перезаряжанием'
        return division

    def get(self, request, event_id):
        """получить pdf с результатами по дисциплине"""
        
        PAGE_SIZE = settings.ATLIMA_PROTOCOL_PAGE_SIZE        
        # устанавливаем имя протокола и путь к нему
        # будет лежать в media/protocols/protocol_event_event_id.pdf
        media_path = settings.MEDIA_ROOT + "/protocols/"
        protocol_name = f'protocol_event_{event_id}.pdf'
        path = f'{media_path}{protocol_name}'


        # пробуем получить ивент
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {'event_id': ['event not found']}}, status=404)
        
        serializer = EventMenuSerializer
        serialized = serializer(event, context={"request": request})
        data = serialized.data

        disciplines = Slot.objects.filter(
            paid=True, 
            active=True, 
            event=event).values_list('discipline', flat=True).distinct()
        disciplines = Discipline.objects.filter(id__in=disciplines).all()
        protocol_number = 0

        for discipline in disciplines:

            # TODO: номер протокола должен браться откуда-то
            protocol_number += 1
            # TODO: перенести в функцию получения всех данных для протокола
            title = data['title']
            location = data['location']
            event_date = data['start_event_date'][:10]
            city = data['city']['title']


            serializer = DisciplineSerializer
            serialized_discipline = serializer(discipline, context = {'request': request})
            abbreviation = serialized_discipline["division"]["description_ru"]
            
            weapon = discipline.division.weapon.id
            weapon = Weapon.objects.get(id=weapon)
            weapon = Weapon.objects.filter(weapon = weapon, 
                                                                language__code="ru").first()
            # weapon = weapon.title

            division = discipline.division.name_ru
            division = self._get_division_name(division)

            discipline_text = f"{abbreviation} - {weapon}, {division}. Мужчины и женщины."

            evsk = data['evsk']
            evsk_instance = EventEVSKStatus.objects.get(id=evsk['id'])
            evsk_name = evsk_instance.name

           # buffer = io.BytesIO()
            p = canvas.Canvas(path)

            styles = getSampleStyleSheet() # дефолтовые стили
            styles['Normal'].fontName='Arial'
            pdfmetrics.registerFont(TTFont('Arial','Arial.ttf', 'UTF-8'))
            pdfmetrics.registerFont(TTFont('Arial_Bold','Arial_Bold.ttf', 'UTF-8'))
            
            # устанавливаем русскоязычный Arial
            p.setFont('Arial', 10)

            protocol_header = f"ПРОТОКОЛ №{protocol_number}"
            proto = []

            # объявление стилей
            header_proto_style = ParagraphStyle('ProtocolHeader',
                            fontName="Arial_Bold",
                            fontSize=14,
                            parent=style['Heading1'],
                            alignment=1,
                            spaceAfter=15)

            event_title_style = ParagraphStyle('EventHeader',
                            fontName="Arial_Bold",
                            fontSize=10,
                            alignment=1,
                            spaceAfter=5)

            location_spaced_style = ParagraphStyle('Location',
                            fontName="Arial_Bold",
                            fontSize=10,
                            alignment=1,
                            spaceAfter=10)

            discipline_style = ParagraphStyle('Discipline',
                            fontName="Arial_Bold",
                            parent=style['Normal'],
                            spaceAfter=10)

            date_and_city_spacing = ParagraphStyle('AdditionalSpacingNormal',
                                fontName="Arial",
                                spaceBefore=25,
                                spaceAfter=10)

            referee_spacing = ParagraphStyle('AdditionalRefereeSpacing',
                                fontName="Arial",
                                spaceBefore=40)

            aligned_table_header = ParagraphStyle('TableHeader',
                                fontName = "Arial_Bold",
                                fontSize=10,
                                alignment=1)

            aligned_table_value = ParagraphStyle('TableCell',
                                fontName='Arial',
                                fontSize=10,
                                alignment=1)

            region_decreased = ParagraphStyle('Region',
                                fontName='Arial',
                                fontSize=10)

            
            dt = datetime.datetime.now()

            dt = dt.strftime("%d.%m.%Y")
            date = datetime.datetime.strptime(event_date, "%Y-%m-%d")
            date = date.strftime("%d.%m.%Y")

            proto.append(Paragraph(protocol_header, header_proto_style))
            proto.append(Paragraph(evsk_name.upper(), event_title_style))
            proto.append(Paragraph(title, event_title_style))
            proto.append(Paragraph("проходившего "+ f"{date}" + " по адресу:", event_title_style))
            proto.append(Paragraph(location, location_spaced_style))
            proto.append(Paragraph(f"{dt} г." + ' &nbsp;'*72 + f"г. {city}", date_and_city_spacing))
            proto.append(Paragraph(discipline_text, discipline_style))

            protocol_table = []
            table_header = [Paragraph('Место', aligned_table_header), 
                                    Paragraph('%', aligned_table_header),
                                    Paragraph('Очки', aligned_table_header), 
                                    Paragraph('Участник', aligned_table_header), 
                                    Paragraph('Дата рождения', aligned_table_header), 
                                    Paragraph('Регион', aligned_table_header),
                                    Paragraph('Звание/разряд', aligned_table_header)]
            protocol_table.append(table_header)

            table_data = self._comstock_by_discipline(event, discipline)
            place = 1
            row_counter = 0
            colwidths = (43, 38, 60, 180, 70, 130, 55)

            table_size = len(table_data)
            
            from math import ceil
            pages = ceil(table_size / PAGE_SIZE)
            page_counter = 0

            for data in table_data:
                slot = data['slot']
                percentage = data['percentage']
                stage_points = data['stage_points']

                # проверяем, есть ли на слоте пользователь и если есть, считаем результаты
                # в штатном режиме. Иначе смотрим импортированные свойства слота
                user = slot['user']
                
                if user is not None:
                    
                    profile = user
                    if profile is not None:
                        pfn = profile.native_firstname
                        pln = profile.native_lastname
                        pp = profile.native_patronym
                        birth_date = profile.birth_date
                        birth_date = str(birth_date.strftime("%d.%m.%Y"))
                        if profile.region is not None:
                            region = Paragraph(profile.region.title, styles['Normal'])
                        else:
                            region = Paragraph('-', styles['Normal'])    
                    else:
                        pfn = user['first_name']
                        pln = user['last_name']
                        pp = '-'
                        birth_date = '-'
                        region = '-'
                        qualification = '-'
                    username = Paragraph(f"{pln} {pfn} {pp}", styles['Normal'])
                    qualification = OfficialQualification.objects.filter(qualification=1, user__id=user['id']).first()
                    if qualification is None:
                        qualification = Paragraph("-", style=aligned_table_value)
                    else:
                        qualification = Paragraph(str(qualification.category), style=aligned_table_value)
                else:
                    username = Paragraph(translit(slot['imported_name'], 'ru'), styles['Normal'])
                    birth_date = "-"
                    region = "-"
                    qualification = "-"

                # каждое значение обёрнуто в параграф со своим стилем и отступом
                row = [Paragraph(str(place), aligned_table_value), 
                    Paragraph(str(percentage), aligned_table_value), 
                    Paragraph(str(stage_points), aligned_table_value), 
                    username, 
                    Paragraph(str(birth_date), aligned_table_value), region, qualification]
                protocol_table.append(row)
                row_counter += 1
                
                # заполнение таблицы результатов
                frame = Frame(0, 0, 21*cm, 29.7*cm, leftPadding=cm, bottomPadding=cm, rightPadding=cm, topPadding=cm,)
                if row_counter == PAGE_SIZE:
                    page_counter += 1
                    protocoltable = Table(protocol_table, colwidths)
                    protocoltable.setStyle(TableStyle([('INNERGRID', (0,0), (-1,-1), 0.25, colors.black), ('BOX', (0,0), (-1,-1), 0.25, colors.black)]))
                    proto.append(protocoltable)
                    p.setFont('Arial', 10)
                    frame.addFromList(proto, p)
                    p.drawString(200, 20, u"Результаты рассчитаны в программе Atlima".encode('utf-8'))
                    p.drawString(550, 20, f"{page_counter} / {int(pages)}")
                    if page_counter < pages:
                        p.showPage()
                    row_counter = 0
                    protocol_table = []
                    proto = []
                
                place += 1

            # оставшиеся строки, не вошедшие в предыдущий набор

            if row_counter != 0:
                frame = Frame(0, 0, 21*cm, 29.7*cm, leftPadding=cm, bottomPadding=cm, rightPadding=cm, topPadding=cm,)
                protocoltable = Table(protocol_table, colwidths)
                protocoltable.setStyle(TableStyle([('INNERGRID', (0,0), (-1,-1), 0.25, colors.black), ('BOX', (0,0), (-1,-1), 0.25, colors.black)]))
                proto.append(protocoltable)
                p.setFont('Arial', 10)
                p.drawString(550, 20, f"{pages} / {pages}")
                row_counter = 0
                protocol_table = []

            # заполнение главного судьи и главного секретаря события
            # 1 - Главный Судья, 3 - Главный Секретарь
            main_referee = RefereeSlot.objects.filter(event = event, role = 1).first()
            if main_referee is not None:
                main_referee_user = main_referee.user
                main_referee_profile = main_referee.user
                if main_referee_profile is not None:
                    if main_referee_profile.native_firstname is not None:
                        mrfn = main_referee_profile.native_firstname[0]
                    else:
                        mrfn = translit(main_referee_user.first_name, language_code="ru")[0]

                    if main_referee_profile.native_lastname is not None:
                        mrln = main_referee_profile.native_lastname
                    else:
                        mrln = translit(main_referee_user.last_name, language_code="ru")
                    
                    if main_referee_profile.native_patronym:
                        mrp = main_referee_profile.native_patronym[0]
                    else:
                        if main_referee_profile.patronym:
                            mrp = translit(main_referee_profile.patronym, language_code="ru")[0]
                        else:
                            mrp = ""
                    if mrp != "":
                        mrname = f"{mrln} {mrfn}. {mrp}."
                    else: 
                        mrname = f"{mrln} {mrfn}."
                else: 
                    mrname = "-"
            else:
                mrname = "-"
            main_secretary = RefereeSlot.objects.filter(event=event, role = 3).first()
            if main_secretary is not None:
                main_secretary_user = main_secretary.user
                main_secretary_profile = main_secretary_user
                if main_secretary_profile is not None:
                    if main_secretary_profile.native_firstname is not None:
                        msfn = main_secretary_profile.native_firstname[0]
                    else:
                        msfn = translit(main_secretary_user.first_name, language_code='ru')[0]
                    if main_secretary_profile.native_lastname is not None:
                        msln = main_secretary_profile.native_lastname
                    else:
                        msln = translit(main_secretary_user.last_name, language_code='ru')
                    if main_secretary_profile.native_patronym is not None:
                        msp = main_secretary_profile.native_patronym[0]
                    else:
                        msp = translit(main_secretary_profile.patronym, language_code="ru")[0]
                    msname = f"{msln} {msfn}. {msp}."
                else:
                    msname = "-"
            else:
                msname = "-"
            proto.append(Paragraph(f"Главный судья:" + ' &nbsp;'*45 + f"{mrname}", referee_spacing))
            proto.append(Paragraph(f"Главный секретарь:" +  ' &nbsp;'*41 + f"{msname}", referee_spacing))
            
            frame.addFromList(proto, p)
            p.drawString(200, 20, u"Результаты рассчитаны в программе Atlima".encode('utf-8'))
            p.showPage()
            p.save()

            event.save()

        return JsonResponse({"status": True})
    


# ПОЛУЧИТЬ ТЕКУЩИЕ ОЦЕНКИ СУДЕЙ
class CurrentRefereeGrades(APIView):

    def get(self, request, event_id):

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {'event_id': ['event not found']}}, status=404)
        rgserializer = RGSerializer
        rgs = RefereeGrade.objects.filter(event=event)
        serialized = rgserializer(rgs, many=True)
        return JsonResponse(serialized.data, safe=False)
    
    
class GradeRefereeWork(APIView):
    """Оценка работы судей"""
    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {'event_id': ['event not found']}}, status=404)
        
        referee_slots = RefereeSlot.objects.filter(event=event).all()
        serializer = RefereeSlotSerializer
        serialized = serializer(referee_slots, many=True)
        data = serialized.data
        return JsonResponse(data, safe=False)

    def post(self, request, event_id):
            data = request.data

            try:
                grades = data['grades']
            except KeyError:
                return JsonResponse({"status": False, "errors": {"grades": ['grades array not found']}}, 400)

            try:
                event = Event.objects.get(id=event_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {'event_id': ['event not found']}}, status=404)
            
            for item in grades:
                try:
                    referee_id = item['referee_slot_id']
                    referee_grade = item['grade']
                except KeyError as ke:
                    error = str(ke)
                    return JsonResponse({"status": False, "errors": {f"{error}": "required parameter"}}, status=400)
                try:
                    referee_slot = RefereeSlot.objects.get(id=referee_id)
                    new_referee_grade = RefereeGrade.objects.create(referee_slot = referee_slot,
                                                                event=event,
                                                                grade=referee_grade)
                    new_referee_grade.save()
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "errors": {"referee_slot_id": ["referee_slot_id is not exists"]}}, status = 400)

            event.completed = True
            event.registration_opened = False
            event.save()  

            referee_invites = EventRefereeInvite.objects.filter(event=event, status__in=(EventRefereeInvite.WAITING, EventRefereeInvite.MODERATED)).all()
            referee_invites.delete()

            participant_trash_slots = Slot.objects.filter(Q(paid=False)|Q(active=False)|Q(user__isnull=True)).all()
            participant_trash_slots.delete()

            users_interested_in = UserInterestedIn.objects.filter(event=event).all()
            users_interested_in.delete()

            invited_notifications = Notification.objects.filter(notification_template__system_event_type__title='event_participant_invite', event=event, is_readed=False).all()
            invited_notifications.delete()


            return JsonResponse({"status": True})


# СЛОТ СУДЬИ, СОЗДАЁТСЯ ПОСЛЕ АППРУВА ПРИГЛОСА
class RefereesSlots(APIView):
    def get(self, request, event_id):
        if request.version == "1.0" or request.version is None:
            try:
                event = Event.objects.get(id=event_id)
                serializer = RefereeSlotSerializer
                referee_slots = RefereeSlot.objects.filter(event=event).all()
                if referee_slots is not None:
                    serialized = serializer(referee_slots, many=True)
                    data = serialized.data
                else:
                    data = []
            except ObjectDoesNotExist:
                return JsonResponse({"status": False}, status=404)
            
            return JsonResponse(data, safe=False)



class CheckCurrentUserIsReferee(APIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request, event_id):
        user = request.user
        # проверим наличие события
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "No event with provided ID"}, status=400)
        # проверим наличие записи о судействе в данном событии
        check_is_referee = EventRefereeInvite.objects.filter(Q(event=event) & Q(status=2) & Q(user=user)).first()
        if check_is_referee is None:
            return JsonResponse({"status": False})
        return JsonResponse({"status": True})



class TargetSetUpdateAPI(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    # обновление
    # обновить группу мишеней в упражнении
    def put(self, request, target_group_id):
        data = request.data

        # проверим смену типа мишени
        target_type_id = data.get("target_type_id")
        
        try:
            target_type = Target.objects.get(id=target_type_id)
        except ObjectDoesNotExist:
            target_type = None
            
        amount = data.get("amount")
        alpha = data.get("alpha")

        try:
            target_set = TargetSet.objects.get(id=target_group_id)

            # проверка упражнения на наличие результатов
            # если результаты есть, упражнение нельзя править
            check_course = target_set.course_target_array
            check_course_results = AggregatedCourseResultForSlot.objects.filter(course=check_course).all()
            if check_course_results.count() > 0:
                return JsonResponse({"status": False, "message": "this course already has results"}, status=400)
        

            # количество очков за A
            if alpha:
                if alpha not in (5, 10, 15,):
                    return JsonResponse({"status": False, "message": "Alpha can be only 5, 10 or 15 points"}, status=400)
                target_set.alpha_cost = alpha

            # количество мишеней и тип мишени, если переданы
            target_set.amount = amount if amount is not None else target_set.amount
            target_set.target_type = target_type if target_type is not None else target_set.target_type
            target_set.save()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Target set is not found"}, status=404)
        return JsonResponse({"status": True})

    # удалить группу мишеней в упражнении
    def delete(self, request, target_group_id):
        try:
            target_set = TargetSet.objects.filter(id=target_group_id).first()

            course = target_set.course_target_array
            target_sets_in_course = course.objects.all()
            target_sets_amount_in_course = target_sets_in_course.count()

            if target_sets_amount_in_course == 1:
                return JsonResponse({"status": False, "message": "cant delete last target set in course"}, status=400)
            
            check_course = target_set.course_target_array
            check_course_results = AggregatedCourseResultForSlot.objects.filter(course=check_course).all()
            if check_course_results.count() > 0:
                return JsonResponse({"status": False, "message": "this course already has results"}, status=400)

            target_set.delete()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "no target set found"})

        return JsonResponse({"status": True})


# Методы для создания мишеней
class TargetSetCreationAPI(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    # добавить группу мишеней в упражнение
    def post(self, request, course_id):
        data = request.data
        try:
            course = Course.objects.get(id=course_id)
            
            check_course_results = AggregatedCourseResultForSlot.objects.filter(course=course).all()
            if check_course_results.count() > 0:
                return JsonResponse({"status": False, "message": "this course already has results"}, status=400)

            target_type = data['target_type_id']
            alpha_points = data['alpha']
            amount = data['amount']
            if alpha_points not in (5, 10, 15,):
                return JsonResponse({"status": False, "message": "Alpha can be only 5, 10 or 15 points"}, status=400)
            target_instance = Target.objects.get(id=target_type)
            new_target_set = TargetSet.objects.create(target_type=target_instance, 
                                                    course_target_array=course, 
                                                    amount=amount, 
                                                    alpha_cost=alpha_points)
            new_target_set.save()
        except KeyError:
            return JsonResponse({"status": False, "message": "target_type_id, alpha and amount is required"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Event not found"}, status=404)
        return JsonResponse({"status": True, "id": new_target_set.id})



# обновление упражнения
class UpdateCourseAPI(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    # Обновить упражнение
    def put(self, request, course_id):

        data = request.data

        title = data.get("title")
        scoring_shoots = data.get("scoring_shoots")
        minimum_shoots = data.get("minimum_shoots")
        descriptions = data.get("descriptions")
        targets = data.get("targets")


        try:
            course = Course.objects.get(id=course_id)

            check_course_results = AggregatedCourseResultForSlot.objects.filter(course=course).all()
            if check_course_results.count() > 0:
                return JsonResponse({"status": False, "message": "this course already has results"}, status=400)

            event = course.event

            course.title = title if title is not None else course.title
            course.scoring_shoots = scoring_shoots if scoring_shoots is not None else course.scoring_shoots
            course.minimum_shoots = minimum_shoots if minimum_shoots is not None else course.minimum_shoots

            if descriptions:
                for description in descriptions:
                    language_id = description['language_id']
                    text = description['description']
                    language = settings.LANGUAGES[language_id][0]
                    
                    course.set_language(language)
                    course.description = description['description']
                    course.save()

            if targets:

                old_targets = TargetSet.objects.filter(course_target_array=course).all()
                old_targets.delete()

                for target_set in targets:
                    target_type_id = target_set['target_type_id']
                    alpha = target_set['alpha']
                    amount = target_set['amount']

                    # если не находим нужный тип мишени, устанавливаем в null
                    try:
                        target_instance = Target.objects.get(id=target_type_id)
                    except ObjectDoesNotExist:
                        target_instance = None
                    
                    # Значение А жёстко регламентировано, при отсутствии A берём 5
                    alpha = alpha if alpha in [5,10,15] else 5

                    target_set = TargetSet.objects.create(target_type=target_instance, course_target_array=course, amount=amount, alpha_cost=alpha)
                    target_set.save()
        
            course.save()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Event not found"}, status=404)
        course.save()
        return JsonResponse({"status": True})

    # изменить сквозную нумерацию упражнений
    def reorganize_courses_numbers(self, course):
        course_number = course.course_number
        reorganized_courses = Course.objects.filter(course_number__gt=course_number).all()

        for reorganize_course in reorganized_courses:
            old_number = reorganize_course.course_number
            new_number = old_number - 1
            reorganize_course.course_number = new_number
            reorganize_course.save()

        return JsonResponse({"status": True})

    # удалить упражнение
    def delete(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)

            course_results = AggregatedCourseResultForSlot.objects.filter(course=course).all()
            if course_results.count() > 0:
                return JsonResponse({"status": False, "message": "cant delete course with results"}, status=400)

            course.delete()
            self.reorganize_courses_numbers(course)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Object not found"}, status=404)
        return JsonResponse({"status": True})


# добавление и обновление курсов

# создать описания
def add_descriptions(course, descriptions):
    # заполняем описания
    for description in descriptions:
        # получим параметры из запроса
        try:
            language_id = description['language_id']
            description_text = description['description']
        except KeyError:
            pass
        # добавим новое описание упражнения для каждого языка
        new_course = Course.objects.create(
            description = description_text
        )
        
        # try:
        #     language = ContentLanguageAdapter.objects.get(id=language_id)
        #     new_description = CourseDescription.objects.create(language=language, course=course, description=description_text)
        #     new_description.save()
        # except ObjectDoesNotExist:
        #     pass


# Обновление ганчека
class GuncheckUpdateAPI(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def put(self, request, guncheck_id):
        """добавление фото в ганчек"""
        try:
            guncheck = AggregatedCourseResultForSlot.objects.get(id=guncheck_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "no guncheck found"}, status=404)
        
        try:
            data = request.data['photo']
        except KeyError:
            return JsonResponse({"status": False, "message": "no photo provided"}, status=400)

        guncheck.photo = data
        guncheck.save()
        return JsonResponse({"status": True})

    def delete(self, request, guncheck_id):
        """отмена Guncheck"""
        try:
            guncheck = AggregatedCourseResultForSlot.objects.get(id=guncheck_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "no guncheck found"}, status=404)
        guncheck.active = False
        guncheck.delete_timestamp = datetime.datetime.now()
        guncheck.save()
        return JsonResponse({"status": True})
    
    
# ГАНЧЕК
# фиксируется судьёй матча с фото
# правая / левая рука и 
class GuncheckInterface(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, slot_id):
        """Добавление Guncheck для пользователя"""
        data = request.data
        referee_user = request.user
        try:
            client_id = data['client_id']
            discipline = data['discipline']
            category = data['category']
            power_factor = data['power_factor']
            strong_hand = data['strong_hand']
            timestamp = data['timestamp']
            slot = Slot.objects.get(id=slot_id)
        except KeyError as ke:
            error = str(ke)
            return JsonResponse({"status": False, "message": f"{error}"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "slot not found"}, status=404)

        try:
            discipline = Discipline.objects.get(id=discipline)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "discipline not found"}, status=404)

        referee_slot = RefereeSlot.objects.filter(user=referee_user, event=slot.event).first()
        if referee_slot is None:
            return JsonResponse({"status": False, "errors": {'referee_slot': ['referee slot not found for you']}}, status=404)
        
        unique = AggregatedCourseResultForSlot.objects.filter(result_type=AggregatedCourseResultForSlot.GUNCHECK, slot=slot, timestamp=timestamp, referee_slot=referee_slot).first()
        if unique is not None:
            return JsonResponse({"status": False, "message": {"guncheck": ['not unique']}})

        new_guncheck = AggregatedCourseResultForSlot.objects.create(slot = slot,
                                                                    client_id = client_id,
                                                                    result_type = AggregatedCourseResultForSlot.GUNCHECK,
                                                                    discipline = discipline,
                                                                    category = category,
                                                                    power_factor = power_factor,
                                                                    strong_hand = strong_hand,
                                                                    referee_slot = referee_slot,
                                                                    timestamp = timestamp)
        new_guncheck.save()

        slot.discipline = discipline
        slot.category = category
        slot.power_factor = power_factor
        slot.user.strong_hand = strong_hand
        slot.save()

        return JsonResponse({"status": True, "id": new_guncheck.id})
    
    
# СОЗДАНИЕ УПРАЖНЕНИЯ
class CourseFullFlow(APIView):
    def post(self, request, event_id):
        # проверяем наличие события
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "event not found"}, status=404)
        
        # добавляем новое упражнение в соответствии с переданными данными
        data = request.data

        title = data.get("title")
        scoring_shoots = data.get("scoring_shoots")
        minimum_shoots = data.get("minimum_shoots")
        scoring_paper = data.get("scoring_paper")
        descriptions = data.get("descriptions")
        targets = data.get("targets")

        title = title if title is not None else "Без имени"
        scoring_shoots = scoring_shoots if scoring_shoots is not None else 0
        minimum_shoots = minimum_shoots if minimum_shoots is not None else 0
        scoring_paper = scoring_paper if scoring_paper is not None else 0

        # получаем новый номер упражнения
        courses_in_event = Course.objects.filter(event=event).all()
        new_course_number = courses_in_event.count() + 1
        
        # создаём экземпляр упражнения
        new_course = Course.objects.create(event=event, 
                                        course_number=new_course_number,
                                        title = title,
                                        scoring_shoots = scoring_shoots,
                                        minimum_shoots = minimum_shoots,
                                        scoring_paper = scoring_paper)
        new_course.save()

        if descriptions:
            add_descriptions(new_course, descriptions)

        if targets:
            for target_set in targets:
                target_type_id = target_set['target_type_id']
                alpha = target_set['alpha']
                amount = target_set['amount']

                # если не находим нужный тип мишени, устанавливаем в null
                try:
                    target_instance = Target.objects.get(id=target_type_id)
                except ObjectDoesNotExist:
                    target_instance = None
                
                # Значение А жёстко регламентировано, при отсутствии A берём 5
                alpha = alpha if alpha in [5,10,15] else 5
                new_target_set = TargetSet.objects.create(target_type=target_instance, 
                                                        course_target_array=new_course, 
                                                        amount=amount, 
                                                        alpha_cost=alpha)
                new_target_set.save()

        return JsonResponse({"status": True, "id": new_course.id})
    
    

# ПОДНЯТЬ ИЛИ ОПУСТИТЬ УПРАЖНЕНИЕ В СПИСКЕ
class MoveCourseInList(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def put(self, request, course_id):
        data = request.data

        try:
            direction = data['direction']
            course = Course.objects.get(id=course_id)
        except KeyError:
            return JsonResponse({"status": False, "message": "direction is required"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "course not found"}, status=404)

        if direction.lower() == 'up':
            course_number = course.course_number
            if course_number != 1: 
                prev_course_number = course.course_number - 1
                prev_course = Course.objects.get(course_number=prev_course_number, event=course.event)
                prev_course.course_number = course_number
                prev_course.save()
                course.course_number = prev_course_number
                course.save()
                return JsonResponse({"status": True})
            else:
                return JsonResponse({"status": False, "message": "course on the top"}, status=400)
        elif direction.lower() == 'down':
            course_number = course.course_number
            courses_overall = Course.objects.filter(event=course.event).all()
            course_overall = courses_overall.count()

            if course_number != course_overall: 
                next_course_number = course.course_number + 1
                next_course = Course.objects.get(course_number=next_course_number, event=course.event)
                next_course.course_number = course_number
                next_course.save()
                course.course_number = next_course_number
                course.save()
                return JsonResponse({"status": True})
            else:
                return JsonResponse({"status": False, "message": "course in the end of list"}, status=400)
        else:
            return JsonResponse({"status": False, "message": "direction can be up or down"}, status=400)


class GetUserQualification(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]
    
    def _self_qualification(self, request):
        qualification = OfficialQualification.objects.filter(
            user = request.user
        ).order_by('-qualification', 'IROA')
        return qualification

    def get(self, request, sport_id):
           
        user_id = request.GET.get('user_id', None)

        if user_id is None:
            user = request.user
        else:
            try:
                user = User.objects.get(id=user_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"user_id": ["not found"]}}, status=400)
        
        serializer = OfficialQualificationSerializer
            
        try:
            sport = Sport.objects.get(id=sport_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"sport_id": ["not found"]}}, status=400)
        
        qualifications = OfficialQualification.objects.filter(user=user, sport_type=sport, approved=True).all()

        highest_qualification = self.get_highest_initiator_qualification(qualifications)

        if highest_qualification is not None:
            serialized = serializer(highest_qualification)
            result = serialized.data
        else:
            result = None

        return JsonResponse(result, safe=False)
       

class UnconditionalRefereeRequestApprove(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, invite_id):
        event_invite = EventRefereeInvite.objects.get(id=invite_id)
        event_invite.status = EventRefereeInvite.APPROVED
        referee_slot, created = RefereeSlot.objects.get_or_create(user = event_invite.user, event=event_invite.event, role=event_invite.role)
        referee_slot.save()
        event_invite.save()
        return JsonResponse({"status": True})


class UnconditionalRefereeRequestDismiss(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request, invite_id):
        data = request.data
        try:
            dismiss_reason = data['dismiss_reason']
        except KeyError:
            return JsonResponse({"status": False, "message": "No dismiss_reason passed"}, status=400)
        
        event_invite = EventRefereeInvite.objects.get(id=invite_id)
        event_invite.status = EventRefereeInvite.DISMISSED
        event_invite.dismiss_reason = dismiss_reason
        event_invite.save()

        return JsonResponse({"status": True})
    
    
class GetRefereeList(APIView):
    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Event not found"}, status=404)
    
        referees = EventRefereeInvite.objects.filter(event=event).all()
        serializer = RefereeInviteSerializer
        serialized = serializer(referees, many=True)
    
        return JsonResponse(serialized.data, safe=False)


class DismissRefereeInvite(APIView):

    def put(self, request, invite_id):
        data = request.data
        request_user = request.user

        # получим данные по инвайту
        try:
            invite = EventRefereeInvite.objects.get(id=invite_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Invite is not exist"}, status=404)

        # проверим роль пользователя, который делает запрос, на мероприятии
        try:
            approved_invite = EventRefereeInvite.objects.get(event=invite.event, user=request_user, status=EventRefereeInvite.APPROVED)
        except ObjectDoesNotExist:
            approved_invite = None
        
        reason = data.get('dismiss_reason')
        if reason:
            invite.status = EventRefereeInvite.DISMISSED
            invite.dismiss_reason = reason
            invite.save()
        
        if reason is None:
            invite.delete()

        return JsonResponse({"status": True})
    
    
    
class ApproveRefereeInvite(APIView):

    def get_role_from_number(numeric_role):

        if numeric_role == 1:
            role = 'Main Referee'
        elif numeric_role == 2:
            role = 'Main Referee Deputy'
        elif numeric_role == 3:
            role = 'Main Secretary'
        elif numeric_role == 4:
            role = 'Referee'
        
        return role

    def get_user_role(self, request_user, profile, event):

        role = None
        # сначала проверим, является ли пользователь администратором мероприятия
        event_admin = EventAdministration.objects.filter(event=event, user=profile).first()
        if event_admin is not None:
            if event_admin.is_director is False:
                role = "Event Administrator"
            else:
                role = "Director"
        
        # если он не администратор мероприятия, то ищем запись в судьях
        referee = EventRefereeInvite.objects.filter(event=event, user=request_user, status=EventRefereeInvite.APPROVED).first()
        
        if referee is not None:
            numeric_role = referee.role
            role = self.get_role_from_number(numeric_role)
        
        if role is None:
            return JsonResponse({"status": False, "message": "User is not admin or referee for this event"}, status=400)
        return role

    def get(self, request, invite_id):
        """Получение параметров для отображения ролей пригласителя и приглашаемого"""
        # cначала нужно получить создателя заявки, поле created_by
        event_invite = EventRefereeInvite.objects.get(id=invite_id)
        event = event_invite.event
        request_user = event_invite.created_by
        profile = request.user
        
        # роль, фамилия и имя создателя заявки
        role_of_invite_creator = self.get_user_role(request_user, profile, event)
        creator_first_name = request_user.first_name
        creator_last_name = request_user.last_name

        # роль приглашаемого на мероприятие судьи
        invited_numeric_role = event_invite.role
        invited_role = self.get_role_from_number(invited_numeric_role)

        result = {
            "initiator": 
            {
            "role": role_of_invite_creator,
            "name": f"{creator_last_name} {creator_first_name}"
            },
            "invited_role": invited_role
            }

        return JsonResponse(result, safe=False)
    
    def put(self, request, invite_id):
        """Подтверждение заявки"""
        request_user = request.user
        request_profile = request_user
        data = request.data

        try:
            referee_invite = EventRefereeInvite.objects.get(id=invite_id)
            event = referee_invite.event
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, 
                                "errors": {"invite_id":["no Invitation with provided id"]}}, 
                                status=404)

        approved_main_referee = EventRefereeInvite.objects.filter(role=EventRefereeInvite.MAIN_REFEREE).first()
        
        role = data.get('role')

        if referee_invite.status != 'WAITING':
            if role is None:
                role = referee_invite.role
            else:                
                referee_slots = RefereeSlot.objects.filter(user=referee_invite.user, event=referee_invite.event).all()
                referee_slots.delete()

        # если нет одобренного главного судьи в событии
        if approved_main_referee is None and role != EventRefereeInvite.MAIN_REFEREE:
            event_admin = EventAdministration.objects.filter(user=request_profile, event=event).first()
            if not event_admin.is_director:
                return JsonResponse({"status": False, 
                "errors":{"no_main_referee": ["you must be director for this action!"]}}, 
                status=400)

        # если это была заявка на ГС, переводим в MODERATED
        # иначе - в APPROVED
        if referee_invite.role == EventRefereeInvite.MAIN_REFEREE:
            referee_invite.status = EventRefereeInvite.MODERATED
        else:
            referee_invite.status = EventRefereeInvite.APPROVED

        referee_invite.role = role        
        referee_invite.save()

        referee_slot = RefereeSlot.objects.create(user=referee_invite.user, 
                                                event=referee_invite.event, 
                                                role=role)
        referee_slot.save()

        return JsonResponse({"status": True})
      

# управление судьями

class CreateRefereeInvite(APIView):
    # добавление приглашения
    def get_available_roles(self, event):
        available_roles = [4]
        try:
            main_referee = EventRefereeInvite.objects.get(event=event, role=1)
        except ObjectDoesNotExist:
            available_roles.append(1)
        
        try:
            main_referee_deputy = EventRefereeInvite.objects.get(event=event, role=2)
        except ObjectDoesNotExist:
            available_roles.append(2)

        try:
            main_secretary = EventRefereeInvite.objects.get(event=event, role=3)
        except ObjectDoesNotExist:
            available_roles.append(3)


        return available_roles

    def post(self, request):

        data = request.data
        request_user = request.user
        
        request_profile = request_user

        try:
            user_id = data['user_id']
            user = User.objects.get(id=user_id)
        except KeyError:
            return JsonResponse({"status": False, "message": "user_id is required"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "user is not exist"}, status=400)

        try:
            event_id = data['event_id']
            event = Event.objects.get(id=event_id)
        except KeyError:
            return JsonResponse({"status": False, "message": "event_id is required"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "event is not exist"}, status=400)

        try:
            role = data['role']
        except KeyError:
            return JsonResponse({'status': "role parameter is required"}, status=400)

        
        if user == request.user:
            check_invite = EventRefereeInvite.objects.filter(event=event, user=user, role=4, status__in=(1,2,4)).all()
        else:
            if role == EventRefereeInvite.MAIN_REFEREE:
                check_invite = EventRefereeInvite.objects.filter(event=event, user=user, role=role, status__in=(2,4))
            else:
                check_invite = EventRefereeInvite.objects.filter(Q(event=event)&Q(user=user)&Q(role=role)&
                                                                Q(status=EventRefereeInvite.APPROVED))

        if check_invite.count() > 0:
            return JsonResponse({"status": False, 
                                "errors": {"user": ["already has invite"]}},
                                status=400)

        force_approve = data.get('force_approve')

        # проверка на наличие отклоненной заявки на судейство на данное мероприятие
        # dismiss_invite_check = EventRefereeInvite.objects.filter(event=event, user=request_user, status=EventRefereeInvite.DISMISSED).first()
        
        # if dismiss_invite_check is not None:
        #     return JsonResponse({"status": False, 
        #                         "message": f"You already tried to register as referee, dismiss reason: {dismiss_invite_check.dismiss_reason}"},
        #                         status=400)

        # если пользователь создаёт заявку на себя, то ему доступна только роль судьи
        if user == request_user:

            role = EventRefereeInvite.REFEREE

            if force_approve:

                new_event_referee_invite = EventRefereeInvite.objects.create(user=user, event=event, role=role,             status=EventRefereeInvite.APPROVED, created_by=request_user)    
                new_event_referee_invite.save()
                referee_slot = RefereeSlot.objects.create(user = new_event_referee_invite.user, event=new_event_referee_invite.event, role=role)

                referee_slot.save()
            else:
                new_event_referee_invite = EventRefereeInvite.objects.create(user=user, event=event, 
                role=role,             status=EventRefereeInvite.WAITING, created_by=request_user)
                new_event_referee_invite.save()
        else:    
            if role == EventRefereeInvite.MAIN_REFEREE:
                try:
                    admin = EventAdministration.objects.get(user=request_profile, event=event)
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, "message": "You are not admin of this event"}, status=400)
                if admin.is_director == False:
                    return JsonResponse({"status": False, "message": "Only director can invite Main Referee"}, status=400)

            if force_approve:

                if role == EventRefereeInvite.MAIN_REFEREE:
                    if event.evsk.regional_status is not None:
                        other_invites = EventRefereeInvite.objects.filter(Q(event=event)&~Q(user=user)&Q(role=role)).all()
                        other_invites.delete()

                        new_event_referee_invite = EventRefereeInvite.objects.create(user=user, event=event, role=role,      status=EventRefereeInvite.MODERATED, created_by=request_user)
                        referee_slot = RefereeSlot.objects.create(user = new_event_referee_invite.user, event=new_event_referee_invite.event, role=role)
                        referee_slot.save()
                    else:
                        other_invites = EventRefereeInvite.objects.filter(Q(event=event)&~Q(user=user)&Q(role=role)).all()
                        other_invites.delete()

                        new_event_referee_invite = EventRefereeInvite.objects.create(user=user, event=event, role=role,      status=EventRefereeInvite.APPROVED, created_by=request_user)
                        referee_slot = RefereeSlot.objects.create(user = new_event_referee_invite.user, event=new_event_referee_invite.event, role=role)
                        referee_slot.save()
                else:
                    new_event_referee_invite = EventRefereeInvite.objects.create(user=user, event=event, role=role,      status=EventRefereeInvite.APPROVED, created_by=request_user)
                    referee_slot = RefereeSlot.objects.create(user = new_event_referee_invite.user, event=new_event_referee_invite.event, role=role)
                    referee_slot.save()
            else:
                new_event_referee_invite = EventRefereeInvite.objects.create(user=user, event=event, role=role,        status=EventRefereeInvite.WAITING, created_by=request_user)
            
            new_event_referee_invite.save()

        return JsonResponse({"status": True})



class AssignParticipantToSquad(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication,]
    permission_classes = [
        IsAuthenticated,
    ]

    def put(self, request):
        data = request.data

        try:
            slot_id = data['slot_id']
            slot = Slot.objects.get(id=slot_id)
        except KeyError:
            return JsonResponse({"status": False, "message": "slot_id is mandatory parameter"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "slot is not found with provided id"}, status=404)

        event = slot.event

        try:     
            squad_number = data['squad_number']
            squad = Squad.objects.get(event=event, squad_number=squad_number)
        except KeyError:
            return JsonResponse({"status": False, "message": "squad_number is mandatory parameter"}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "squad with provided squad_number not found"}, status=404)
        
        properties = EventProperty.objects.get(event=event)
        max_shooters_in_squad = properties.shooters_in_squad
        current_shooters_in_squad = Slot.objects.filter(squad=squad).count()
    
        user = request.user
        profile = user

        if current_shooters_in_squad + 1 > max_shooters_in_squad:
            try:
                event_admin = EventAdministration.objects.get(user=profile, event=event)
                if event_admin.is_director is True:
                    slot.squad = squad
                    slot.save()                
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "message": "only director can assign user to full-packed squad"}, status=400)
        else:
            slot.squad = squad
            slot.save()                

        try:
            create_system_event_object(request.user, 'slot_added_to_squad', {"squad_number": squad.squad_number,
                                                                            "id": event.id})
        except:
            pass

        return JsonResponse({"status": True})


class SquadingRights(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication,]

    def get(self, request, event_id):
        user = request.user
        profile = user

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "event not found"}, status=404)
        
        try:
            event_admin = EventAdministration.objects.get(event=event, user=profile)
        except ObjectDoesNotExist:
            event_admin = None

        if event_admin is not None:
            return JsonResponse({"status": True})
        
        return JsonResponse({"status": False})
    
    
class UnblockSquad(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication,]

    def put(self, request, squad_id):
        try:
            squad = Squad.objects.get(id=squad_id)
            squad.is_blocked = False
            squad.save()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Squad is not found"}, status=404)
        return JsonResponse({"status": True})


# УПРАВЛЕНИЕ СКВОДАМИ
class BlockSquad(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication,]

    def put(self, request, squad_id):
        try:
            squad = Squad.objects.get(id=squad_id)
            squad.is_blocked = True
            squad.save()
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Squad is not found"}, status=404)
        return JsonResponse({"status": True})
