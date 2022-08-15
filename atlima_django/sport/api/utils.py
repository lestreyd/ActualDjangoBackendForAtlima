from atlima_django.sport_events.models import Event, Slot
from atlima_django.users.models import User
from constance import config


# валидные с точки зрения системы слоты
def get_valid_system_slots():
    slots = Slot.objects.filter(event__status=Event.PUBLISH,
                                event__completed=True,
                                event__has_results=True,
                                dont_include_in_rating_calculation=False,
                                active=True,
                                paid=True).exclude(points=0)
    return slots


def get_my_rank(sport, target_user, scope, discipline=None):
        """Подсчёт ранга для каждого участника в системе
        по дисциплине или конкретному виду спорта.
        Для того, чтобы рассчитать рейтинг, используются значения, установленные
        на слотах участников. Начальный рейтинг и значение повышения 
        рейтинга вместе формируют значение рейтинга на текущий момент.
        Это значение мы возьмем с последнего слота, который означает 
        последнее участие человека в событии, где начальный рейтинг устанавливается
        системой в зависимости от того, участвовал ли он ранее в мероприятиях."""
        rating_table = []
        if discipline is None:
            slots = get_valid_system_slots().filter(
                event__sport_type=sport)
        else:
            slots = get_valid_system_slots().filter(
            event__sport_type=sport, 
            discipline=discipline)

        my_rating_slot = slots.filter(user__id=target_user).order_by('-created').first()
        my_user = my_rating_slot.user
        
        # выборка страны и профиля из региона
        # если вдруг по какой-то причине страны или региона не 
        # окажется на профиле, мы обрабатываем
        country = my_rating_slot.user.country
        region = my_rating_slot.user.region


        # смотрим, какой ранг запрашивается. если это ранг для
        # мира, мы просто берём все слоты участников
        if scope == "world":
            slots = slots
        if scope == "country" or scope == "region":
            slotusers = slots.values_list('user', flat=True).distinct()
            # если пришёл запрос по стране, находим всех
            # кто в ней живёт и смотрим их результаты
            if scope == "country":
                if country is not None:
                    profiles = User.objects.filter(
                        country = country, 
                        user_id__in=slotusers
                        ).values_list(
                            "user",
                            flat=True
                        ).distinct()
                else:
                    profiles = None
            # если пришёл регион, отбор делаем по региону
            else:
                if region is not None:
                    profiles = User.objects.filter(
                        region=region,
                        user_id__in=slotusers
                        ).values_list(
                            "user",
                            flat=True
                        ).distinct()
                else:
                    profiles = None
            if profiles:
                # закрываем выборку по стране/региону и находим все слоты
                # с пользователями из конкретной страны или конкретного 
                # региона
                users = User.objects.filter(id__in=profiles).distinct()
                slots = slots.filter(user__in=users).all()
            else:
                slots = None
        if slots is not None:
            if my_rating_slot is not None:
                my_current_rating = my_rating_slot.initial_rating + my_rating_slot.rating_increase
            else:
                my_current_rating = config.INITIAL_RATING

            my_record = {
                "id": my_rating_slot.user.id, 
                "rating": my_current_rating
            }
            
            rating_table.append(my_record)

            all_participants_in_system = slots.values_list(
                'user', flat=True
                ).distinct()

            participants = User.objects.filter(
                id__in=all_participants_in_system
            ).all()
            for participant in participants:
                user_record = {}
                participant_last_slot = slots.filter(
                    user=participant).order_by("-created").first()
                try:
                    participant_rating = participant_last_slot.initial_rating + \
                        participant_last_slot.rating_increase
                except Exception:
                    participant_rating = config.INITIAL_RATING
                
                user_record = {
                    "id": participant.id, 
                "rating": participant_rating}

                rating_table.append(user_record)
            
            ranks = sorted(rating_table, key=lambda d: d['rating'], reverse=True)
            searched_rank_value = None
            for idx, item in enumerate(ranks):
                if item['id'] == target_user:
                    searched_rank_value = idx
                else:
                    searched_rank_value = 0
                if searched_rank_value is None:
                    searched_rank_value = 0
        else:
            searched_rank_value = 0
        # если пользователь будет найден в списке
        # то вернётся его индекс
        return searched_rank_value