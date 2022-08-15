from models import Squad
from django.db.models import Q
from django.http import JsonResponse


def recreate_squads_by_event(event, squads_amount):
    squads_now = Squad.objects.filter(event=event).all()
    amount = squads_now.count()
    if amount > 0:
        if amount > squads_amount:
            for i in range(squads_amount, amount+1):
                squad = Squad.objects.filter(Q(event=event)&Q(squad_number__gte=i))
                squad.delete()
        elif amount < squads_amount:
            need_to_create = (squads_amount - amount) + 1
            new_index = Squad.objects.filter(event=event).latest('squad_number')
            new_index = new_index.squad_number
            for new_squad_number in range(1, need_to_create+1):
                new_index += 1
                new_squad = Squad.objects.create(squad_number=new_index, event=event)
                new_squad.save()
    else:
        for new_squad in range(1, squads_amount+1):
            new_squad_object = Squad.objects.create(event=event, squad_number=new_squad)
            new_squad_object.save()
    return JsonResponse({"status": True})