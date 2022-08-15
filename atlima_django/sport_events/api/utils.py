from atlima_django.sport_events.models import Slot




def get_event_participants(event):
    """ Возвращает словарь с фамилией и именем пользователей, зарегистрированных на мероприятие.
    Выборка осуществляется из слотов, занятых пользователями с фильтрацией по текущему мероприятию.
    Из элементов словаря создаётся список вида
    1. Соловьев Валерий (RU)
    2. Сырыгин Станислав (RU)
    3. Рахимов Жавохир (UZ)
    participants = {"first_name": first_name, "last_name": last_name, "participant_number": participant_number} """
    # забираем только те слоты, для которых есть зарегистрированные пользователи и выводим их
    slots = Slot.objects.filter(event=event, user__isnull=False).all()

    # соберём всех участников из слотов, относящихся к мероприятию
    participants = []
    for slot in slots:
        participant = {}
        # получим все данные из слота
        slots_event = Slot.objects.filter(event=event, 
                                          paid=True, 
                                          active=True, 
                                          user__isnull=False).order_by('created')
        counter = 0
        participant_number = 0

        for slot_event in slots_event:
            counter += 1
            if slot_event.id == slot.id:
                participant_number = counter
                slot.participant_number = participant_number
                slot.save()

        participant_name = f"{slot.user.first_name} {slot.user.last_named}"
        # заполним словарь
        participant['participant_name'] = participant_name
        # participant['participant_number'] = participant_number if participant_number is not None else 0
        if slot.user.country:
            participant['country_code'] = slot.user.country.alpha2
        else:
            participant['country_code'] = None
        participant['user'] = f'/profiles/{slot.user.id}'

        # добавим в массив участников
        participants.append(participant)
    participants = list({v['user']:v for v in participants}.values())
    return participants



