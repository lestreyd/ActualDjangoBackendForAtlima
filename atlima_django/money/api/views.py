from models import Currency, PriceConfiguration
from api.serializers import CurrencySerializer, PriceOptionSerializer
from rest_framework.views import APIView
from django.http import JsonResponse
import requests
from atlima_django.money.models import TransactionHistory, Order, OrderItem
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.sport_events.models import Slot
from atlima_django.money.api.merchant import TinkoffMerchantAPI
from django.template.response import TemplateResponse
from django.http import HttpResponseRedirect
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
import json, simplejson
from rest_framework.permissions import IsAuthenticated
from atlima_django.sport_events.models import Event
from atlima_django.money.api.serializers import PromocodeSerializer
from atlima_django.money.models import PromoCode
import datetime


# TINKOFF_TERMINAL_KEY='1636635934730DEMO'
# TINKOFF_PASSWORD='h8slxbrvng38dw96'

TINKOFF_TERMINAL_KEY = '1636635934730'
TINKOFF_PASSWORD = '35hug73kotf59z9k'


class Currencies(APIView):

    def get(self, request):
        currs = Currency.objects.order_by("-weight_in_list").all()
        serializer = CurrencySerializer
        serialized = serializer(currs, many=True)
        return JsonResponse(serialized.data, safe=False)
    
    
class PriceConfigurations(APIView):

    def get(self, request):
        price_confs = PriceConfiguration
        serializer = PriceOptionSerializer
        serialized = serializer(price_confs, many=True)
        return JsonResponse(serialized.data)



class Pay3DSConfirm(APIView):

    def post (self, request):
        data = request.data

        md = data.get('MD')
        pares = data.get('PaRes')

        datasend= {'MD': md,
                'PaRes': pares}

        r = requests.post('https://securepay.tinkoff.ru/Submit3DSAuthorization', data=datasend)

        response_json = r.json()

        success = response_json.get('Success')
        error_code = int(response_json.get('ErrorCode'))
        payment_status = response_json.get('Status')

        bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.FINISH_AUTHORIZE,
                                                information_type=TransactionHistory.BANK_RESPONSE,
                                                md = md,
                                                success=success,
                                                response = response_json)
        bankresponse.save()

        if success is True and error_code == 0:
            
            # order_id = int(response_json.get('OrderId'))
            payment_id = response_json.get('PaymentId')
            order_id = None

            last_transaction = TransactionHistory.objects.filter(payment_id=payment_id).last()
            
            if last_transaction.operation == TransactionHistory.ADD_CARD or last_transaction.operation == TransactionHistory.ATTACH_CARD:
                order_id = None
            else:
                order_id = last_transaction.order_id

            if order_id is not None:
                try:
                    order = OrderItem.objects.get(order_id=order_id)
                except ObjectDoesNotExist:
                    return JsonResponse({"status": False, 
                                        "errors": {"order_id": ['order not found']}}, 
                                        status=404)
                
                object_type = order.object_type 
                
                if object_type == 'Slot':
                    slot_id = int(order.object_id)
                    slot = Slot.objects.get(id = slot_id)
                    slot.paid = True
                    slot.save()
                else:
                    return HttpResponseRedirect('fail-payment')
                return HttpResponseRedirect('success-payment')
            else:
                return HttpResponseRedirect('success-payment')
        else:
            return HttpResponseRedirect('fail-payment')


class SuccessPayment(APIView):

    def get(self, request):
        if request.version == "1.0" or request.version is None:
            t = TemplateResponse(request, 'success.html')
            t.render()
            return t
        else:
            t = TemplateResponse(request, 'success.html')
            t.render()
            return t


class FailPayment(APIView):
    
    def get(self, request):
        if request.version == "1.0" or request.version is None:
            t = TemplateResponse(request, 'fail.html')
            t.render()
            return t
        else:
            t = TemplateResponse(request, 'fail.html')
            t.render()
            return t        
        

class CardList(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request):
        user = request.user
        userid = user.id
        merchant = TinkoffMerchantAPI(terminal_key=TINKOFF_TERMINAL_KEY,
                                    secret_key=TINKOFF_PASSWORD)
        response = merchant.getCardList(CustomerKey=f'user-{userid}')    
        answer = response.json()
        try:
            err = answer['ErrorCode']
        except Exception:
            err = None
        
        unified_list = []

        if err:
            return JsonResponse([], safe=False)
        else:
            for card in answer:
                if card['Status'] != 'D':
                    
                    unified_card = {}
                    
                    unified_card['id'] = card['CardId']
                    unified_card['card_number'] = card['Pan']
                    unified_card['status'] = card['Status']
                    unified_card['exp'] = card['ExpDate']

                    if card['Status'] == 'I':
                        unified_card['active'] = False
                    elif card['Status'] == 'A':
                        unified_card['active'] = True 

                    unified_list.append(unified_card)

            return JsonResponse(unified_list, safe=False)


class CancelPayment(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        data = request.data

        try:
            payment_id = data['payment_id']
        except KeyError:
            return JsonResponse({"status": False, "errors": {'payment_id': ['payment_id is required']}}, status=400)
        
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
            return JsonResponse({"status": True})
        else:
            if message is not None:
                return JsonResponse({"status": False, 'errors': {'message': [f"{message}"]}})
            else:
                return JsonResponse({"status": False})


class RemoveCard(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def delete(self, request, card_id):
        user = request.user
        userid = user.id
        merchant = TinkoffMerchantAPI(terminal_key=TINKOFF_TERMINAL_KEY,
                                    secret_key=TINKOFF_PASSWORD)

        response = merchant.removeCard(CustomerKey=f"user-{userid}", CardId=str(card_id))
        answer = response.json()
        
        success = answer.get('Success')
        status = answer.get('Status')
        error_code = answer.get('ErrorCode')
        message = answer.get('Message')
        details = answer.get('Details')
        
        try:
            bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.REMOVE_CARD,
                                                            information_type=TransactionHistory.BANK_RESPONSE,
                                                            terminal_key=TINKOFF_TERMINAL_KEY,
                                                            customer_key=f"user-{userid}",
                                                            card_id=str(card_id),
                                                            success=success,
                                                            status=status,
                                                            error_code=error_code,
                                                            message=message,
                                                            details=details,
                                                            response=answer)
            bankresponse.save()
        except Exception: # noQA
            pass
        
        if status == 'D':
            return JsonResponse({"status": True})
        else:
            return JsonResponse({"status": False, "errors": {'api error': ['see log in admin site']}}, status=400)


class AddCard(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def post(self, request):
        user = request.user
        userid = user.id
        data = request.data

        card_data = data['card_data']
        info = data.get("data")

        merchant = TinkoffMerchantAPI(terminal_key=TINKOFF_TERMINAL_KEY,
                                    secret_key=TINKOFF_PASSWORD)
        # метод AddCard
        response = merchant.addCard(CustomerKey=f"user-{userid}", CheckType='3DS')
        add_card_result = response.json()

        request_key = success = payment_url = error_code = message = details = None

        request_key = add_card_result.get('RequestKey')
        success = add_card_result.get('Success')
        payment_url = add_card_result.get('PaymentURL')
        error_code = add_card_result.get('ErrorCode')
        message = add_card_result.get('Message')
        details = add_card_result.get('Details')
        payment_id = add_card_result.get('PaymentId')

        try:
            bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.ADD_CARD,
                                                            information_type=TransactionHistory.BANK_RESPONSE,
                                                            terminal_key = TINKOFF_TERMINAL_KEY,
                                                            customer_key=f"user-{userid}",
                                                            request_key = request_key,
                                                            success = success,
                                                            payment_url = payment_url,
                                                            payment_id = payment_id,
                                                            error_code = error_code,
                                                            message = message,
                                                            details = details,
                                                            response=add_card_result)
            bankresponse.save()
        except Exception: # noQA
            pass

        if success == True:
            attach = merchant.attachCard(CardData=card_data, RequestKey=request_key)
            result = attach.json()

            rebill_id = result.get('RebillId')
            card_id = result.get('CardId')
            success = result.get('Success')
            status = result.get('Status')
            error_code = result.get('ErrorCode')
            message = result.get('Message')
            details = result.get('Details')
            md = result.get('MD')
            payment_id = result.get('PaymentId')
            
            try: 
                bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.ATTACH_CARD,
                                                                information_type = TransactionHistory.BANK_RESPONSE,
                                                                terminal_key = TINKOFF_TERMINAL_KEY,
                                                                customer_key=f"user-{userid}",
                                                                card_data = card_data,
                                                                request_key = request_key,
                                                                rebill_id = rebill_id,
                                                                card_id = card_id,
                                                                success = success,
                                                                status = status,
                                                                error_code = error_code,
                                                                message = message,
                                                                details = details,
                                                                payment_id = payment_id,
                                                                md = md,
                                                                response = result)
                bankresponse.save()
            except Exception: # noQA
                pass
            
            status3ds = '3DS_CHECKING'

            if success is True and status != status3ds:
                
                return JsonResponse({"status": True})

            elif success is True and status == status3ds:
                return JsonResponse({"status": True, 
                                    "type": "3DS", 
                                    "transaction_id": bankresponse.id})
            else:
                if message is not None:
                    return JsonResponse({"status": False, "errors": {'message': [f"{message}"]}}, status=400)
                else:
                    if details is not None:
                        return JsonResponse({"status": False, "errors": {'details': [f'{details}']}}, status=400)
                    else:
                        return JsonResponse({"status": False}, status=400)


class Route3DS(APIView):

    def get(self, request, transaction_id):
        if request.version == "1.0" or request.version is None:
            try:
                transaction = TransactionHistory.objects.get(id=transaction_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, 
                                    "errors": {"transaction": ["not found"]}},
                                    status=404)
            
            response = transaction.response
            
            acsurl = response.get('ACSUrl')
            md = response.get('MD')
            pareq = response.get('PaReq')

            t = TemplateResponse(request, 
                                '3ds-payment.html', 
                                {'url': acsurl,  
                                'md': md, 
                                'req': pareq
                                }
                                )
            t.render()
            return t

    
class Payment(APIView):

    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def _get_order(self, order_id):
        order = Order.objects.filter(id=order_id, status=False).first()
        return order

    def _get_order_items(self, order):
        order_items = OrderItem.objects.filter(order_id=order).all()
        return order_items

    def post(self, request, order_id):
        user = request.user
        userid = user.id
        data = request.data

        try:
            card_data = data['card_data']
            save = data['save']
        except KeyError:
            return JsonResponse({"status": False, "errors": {'item': ['Not enought data about item']}}, status=400)

        order = Order.objects.filter(id=order_id).last()
    
        if order is None:
            return JsonResponse({"status": False, "errors": {'order_id': ['order not found']}}, status=404)
        else:
            items = OrderItem.objects.filter(order_id=order)

        try:
            item = items[0]
            amount = item.amount 
        except:
            return JsonResponse({"status": False, "errors": {"items": "not found"}}, status=400)
        # return JsonResponse(dict(items), safe=False)

        if item.object_type.lower() == 'slot':
            
            merchant = TinkoffMerchantAPI(terminal_key=TINKOFF_TERMINAL_KEY,
                                        secret_key=TINKOFF_PASSWORD)

            if save is True:
                # метод AddCard
                response = merchant.addCard(CustomerKey=f"user-{userid}")
                add_card_result = response.json()

                request_key = add_card_result.get('RequestKey')
                success = add_card_result.get('Success')
                payment_url = add_card_result.get('PaymentURL')
                error_code = add_card_result.get('ErrorCode')
                message = add_card_result.get('Message')
                details = add_card_result.get('Details')

                try:
                    bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.ADD_CARD,
                                                                    information_type=TransactionHistory.BANK_RESPONSE,
                                                                    terminal_key = TINKOFF_TERMINAL_KEY,
                                                                    customer_key=f"user-{userid}",
                                                                    request_key = request_key,
                                                                    success = success,
                                                                    payment_url = payment_url,
                                                                    error_code = error_code,
                                                                    message = message,
                                                                    details = details,
                                                                    response=add_card_result)
                    bankresponse.save()
                except Exception: # noQA
                    pass

                if success == True:
                    attach = merchant.attachCard(CardData=card_data, RequestKey=request_key, CheckType='NO')
                    result = attach.json()

                    rebill_id = card_id = success = status = error_code = message = details = None

                    rebill_id = result.get('RebillId')
                    card_id = result.get('CardId')
                    success = result.get('Success')
                    status = result.get('Status')
                    error_code = result.get('ErrorCode')
                    message = result.get('Message')
                    details = result.get('Details')

                    try: 
                        bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.ATTACH_CARD,
                                                                        information_type = TransactionHistory.BANK_RESPONSE,
                                                                        terminal_key = TINKOFF_TERMINAL_KEY,
                                                                        customer_key=f"user-{userid}",
                                                                        card_data = card_data,
                                                                        request_key = request_key,
                                                                        check_type = '3DS',
                                                                        rebill_id = rebill_id,
                                                                        card_id = card_id,
                                                                        success = success,
                                                                        status = status,
                                                                        error_code = error_code,
                                                                        message = message,
                                                                        details = details,
                                                                        response = result)
                        bankresponse.save()
                    except Exception: # noQA
                        pass

            receipt = {}
            receipt['Email'] = user.email
            receipt['Taxation'] = 'osn'
            receipt['Items'] = []

            receipt['Items'].append({'Name': 'Slot', 'Price': amount/100, 'Quantity': 1, "Amount": amount, "Tax": 'vat18'})

            receipt = simplejson.dumps(receipt)
            initial = merchant.init(Amount=str(amount), OrderId=str(order.id), Receipt=json.loads(receipt))
            initial_answer = initial.json()

            success = initial_answer.get('Success')
            status = initial_answer.get('Status')
            payment_id = initial_answer.get('PaymentId')
            error_code = initial_answer.get('ErrorCode')
            payment_url = initial_answer.get('PaymentURL')
            message = initial_answer.get('Message')
            details = initial_answer.get('Details')

            # try:
            bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.INIT,
                                                            information_type=TransactionHistory.BANK_RESPONSE,
                                                            terminal_key=TINKOFF_TERMINAL_KEY,
                                                            amount = amount,
                                                            order_id = order.id,
                                                            success = success,
                                                            payment_id = payment_id,
                                                            error_code = error_code,
                                                            payment_url = payment_url,
                                                            message = message,
                                                            details = details,
                                                            receipt = json.loads(receipt),
                                                            response = initial_answer)
            bankresponse.save()
            # except Exception: # noQA
            #     pass
            
            if status == 'NEW':

                payment = merchant.finishAuthorize(PaymentId=payment_id, CardData=card_data)
                finish_payment = payment.json()

                amount = finish_payment.get('Amount')
                order_id = finish_payment.get('OrderId')
                rebill_id = finish_payment.get('RebillId')
                card_id = finish_payment.get('CardId')
                success = finish_payment.get('Success')
                status = finish_payment.get('Status')
                payment_id = finish_payment.get('PaymentId')
                error_code = finish_payment.get('ErrorCode')
                message = finish_payment.get('Message')
                details = finish_payment.get('Details')
                md = finish_payment.get('MD')

                try:
                    bankresponse = TransactionHistory.objects.create(operation=TransactionHistory.FINISH_AUTHORIZE,
                                                                    information_type = TransactionHistory.BANK_RESPONSE,
                                                                    terminal_key = TINKOFF_TERMINAL_KEY,
                                                                    card_data = card_data,
                                                                    amount = amount,
                                                                    order_id = order_id,
                                                                    rebill_id = rebill_id,
                                                                    card_id = card_id,
                                                                    success = success,
                                                                    status = status,
                                                                    payment_id = payment_id,
                                                                    error_code = error_code,
                                                                    message = message,
                                                                    details = details,
                                                                    md = md,
                                                                    response = finish_payment)
                    bankresponse.save()
                except Exception:
                    pass
                
                payment_valid_statuses = ['CONFIRMED', 'AUTHORIZED']

                if status == '3DS_CHECKING':
                    return JsonResponse({"status": True, 
                                        "type": "3DS",
                                        "transaction_id": bankresponse.id})
                    
                if status in payment_valid_statuses:
                    
                    slot_id = int(item.object_id)
                    slot = Slot.objects.get(id = slot_id)
                    slot.paid = True
                    slot.save()

                    order.status = True
                    order.save()
                    
                    return JsonResponse({"status": True})
                else:
                    if message is not None:
                        return JsonResponse({"status": False, "errors": {'message':[f"{message}"]}}, status=400)
                    elif details is not None:
                        return JsonResponse({"status": False, "errors": {'details':[f"{details}"]}}, status=400)
                    else:
                        return JsonResponse({"status": False}, status=400)
            else:
                if message is not None:
                    return JsonResponse ({"status": False, "errors": {'message': [f"{message}"]}}, status=400)
                else:
                    return JsonResponse ({"status": False}, status=400)



# ПОДСИСТЕМА УПРАВЛЕНИЯ ПРОМОКОДАМИ 

# ГЕНЕРАЦИЯ ПРОМОКОДОВ ДЛЯ ПОЛЬЗОВАТЕЛЯ
class PromocodesView(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id) or Event.objects.get(slug=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "Event not found"}, status=404)

        promocodes = PromoCode.objects.filter(related_event=event).all()
        serializer = PromocodeSerializer
        serialized = serializer(promocodes, many=True)
        result = serialized.data

        return JsonResponse(result, safe=False, status=200)


    def post(self, request, event_id):
        received_json_data = json.loads(request.body)

        discount = received_json_data['discount']
        limit = received_json_data['limit']
        end_date = received_json_data.get('end_date')
        active = received_json_data['active']

        # проверяем мероприятие
        event = None

        try:
            event = Event.objects.get(id=event_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "message": "No event with provided id"}, status=404)

        try:
            amount = received_json_data['amount']
        except KeyError:
            return JsonResponse({"status": False, "message": "Amount is mandatory parameter for generation"}, status=400)

        if amount == 1:

            # забираем все поля из запроса
            title = received_json_data['title']

            # check unique
            try:
                check = PromoCode.objects.get(title=title, related_event=event)
                return JsonResponse({"status": False, "message": "Promocode with this title exists for this event"}, status=400)
            except ObjectDoesNotExist:
                pass 
            
            # title check
            title_length = len(title)
            if title_length < 5 or title_length > 8:
                return JsonResponse({"status": False, "message": "Incorrect title length (5-8)"}, status=400)

            # check discount
            if discount < 0 or discount > 100:
                return JsonResponse({"status": False, "message": "Discount must be 0-100"}, status=400)
            
            # check limit
            if limit < 0 or limit > 1000:
                return JsonResponse({"status": False, "message": "Limit must be 1-1000"}, status=400)
            
            # check end_date
            if end_date:
                from datetime import date, timedelta
                tomorrow = date.today() + timedelta(days=1)
                end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
                
                if end_date.date() < tomorrow:
                    return JsonResponse({"status": False, "message": "Finish date must be not earlier then tomorrow!"}, status=400)
                
                if event.end_event_date:
                    if end_date.date() > event.end_event_date.date():
                        return JsonResponse({"status": False, "message": "Finish date must be not later then end event date!"}, status=400)
                else:
                    if end_date.date() > event.start_event_date.date():
                        return JsonResponse({"status": False, "message": "Finish date must be not later then event date!"}, status=400)

            # если все проверки пройдены, создаём новую запись для события
            new_promocode = PromoCode.objects.create(related_event=event, 
                                                    title=title,
                                                    discount=discount,
                                                    limit=limit,
                                                    finish_date=end_date,
                                                    active=active)
            new_promocode.save()
            return JsonResponse({"status": True, "message": new_promocode.id})
        # можно указать количество генерируемых промокодов
        else:
            if amount < 2 or amount > 1000:
                return JsonResponse({"status": False, "message": "amount must be 2 - 1000 for batch generation"})
            else:
                import random, re
                prefix = received_json_data['prefix']
                
                regex_string = re.compile("^([A-Za-z]{3})+$")
                if not regex_string.match(prefix):
                    return JsonResponse({"status": False, "message": "Prefix must be 3 latin chars"})

                cypher_part = random.sample(range(1,99999), amount)
                titles = [prefix+str(c) for c in cypher_part]

                # check discount
                if discount < 1 or discount > 100:
                    return JsonResponse({"status": False, "message": "Discount must be 0-100"})
                
                # check limit
                if limit < 0 or limit > 1000:
                    return JsonResponse({"status": False, "message": "Limit must be 0-1000"}, status=400)
                    
                # check end_date
                if end_date:
                    from datetime import date, timedelta
                    tomorrow = date.today() + timedelta(days=1)
                    end_date = datetime.strptime(end_date, '%Y-%m-%d')
                    
                    if end_date.date() < tomorrow:
                        return JsonResponse({"status": False, "message": "Finish date must be not earlier then tomorrow!"})
                    
                    if event.end_event_date:
                        if end_date.date() > event.end_event_date.date():
                            return JsonResponse({"status": False, "message": "Finish date must be not later then end event date!"})
                    else:
                        if end_date.date() > event.start_event_date.date():
                            return JsonResponse({"status": False, "message": "Finish date must be not later then event date!"})

                created = 0
                for item in titles:

                    # check unique
                    try:
                        check = PromoCode.objects.get(title=item, related_event=event)
                        continue
                    except ObjectDoesNotExist:
                        pass
                    created += 1
                    # если все проверки пройдены, создаём новую запись для события
                    new_promocode = PromoCode.objects.create(related_event=event, 
                                                            title=item,
                                                            discount=discount,
                                                            limit=limit,
                                                            finish_date=end_date,
                                                            active=active)
                    new_promocode.save()
                
                return JsonResponse({"status": True, "message": f"Created {created} promocodes"}, safe=False, status=200)
                
# УДАЛЕНИЕ ПРОМОКОДА
class PromocodeDelete(APIView):
    """Удаление промокода если не использовался"""
    def put(self, request, promocode_id):
        try:
            promoCode = PromoCode.objects.get(id=promocode_id)
            used = Slot.objects.filter(slot__promocode=promoCode).all().count()
            if used == 0:
                promoCode.delete()
            else:
                return JsonResponse({"status": False, "errors": {"promocode":[f"used {str(used)} times"]}}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"promocode": ['not found']}}, status=404)
        
        return JsonResponse({"status": True})

    def delete(self, request, promocode_id):
        try:
            promoCode = PromoCode.objects.get(id=promocode_id)
            used = Slot.objects.filter(promocode=promoCode).all().count()
            if used == 0:
                promoCode.delete()
            else:
                return JsonResponse({"status": False, "errors": {"promocode":[f"used {str(used)} times"]}}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"promocode": ['not found']}}, status=404)
        
        return JsonResponse({"status": True})


# ОБНОВЛЕНИЕ ПРОМОКОДА
class PromocodeUpdate(APIView):

    authentication_classes = [SessionAuthentication, BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated,]

    def put(self, request, promocode_id):
        received_json_data = json.loads(request.body)

        promocode = PromoCode.objects.get(id=promocode_id)

        discount = received_json_data.get('discount')
        limit = received_json_data.get('limit')
        end_date = received_json_data.get('end_date')
        active = received_json_data.get('active')
        
        # забираем все поля из запроса
        title = received_json_data.get('title')

        used = Slot.objects.filter(promocode=promocode).count()

        if used > 0:
            
            # check limit
            if limit:
                if limit < 1 or limit > 1000:
                    return JsonResponse({"status": False, "message": "Limit must be 1-1000"}, status=400)

                promocode.limit = limit
            
            # check end_date
            if end_date:
                from datetime import date, timedelta
                tomorrow = date.today() + timedelta(days=1)
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                
                if end_date.date() < tomorrow:
                    return JsonResponse({"status": False, "message": "Finish date must be not earlier then tomorrow!"}, status=400)
                event = promocode.related_event
                if event.end_event_date:
                    if end_date.date() > event.end_event_date.date():
                        return JsonResponse({"status": False, "message": "Finish date must be not later then end event date!"}, status=400)
                else:
                    if end_date.date() > event.start_event_date.date():
                        return JsonResponse({"status": False, "message": "Finish date must be not later then event date!"}, status=400)
                promocode.finish_date = end_date
            else:
                promocode.finish_date = None
            
            if active is not None:
                promocode.active = active

            # return JsonResponse({"status": False, "message": f"Promocode was used {used} times, you can change limit, date and activity only"})
        else:
            # check unique
            if title:
                related_event = promocode.related_event
                check = PromoCode.objects.filter(title=title, related_event=related_event).exclude(id=promocode_id).first()

                if check:
                    return JsonResponse({"status": False, "message": "Promocode with this title exists for this event"}, status=400) 
            
                # title check
                title_length = len(title)
                if title_length < 5 or title_length > 8:
                    return JsonResponse({"status": False, "message": "Incorrect title length (5-8)"}, status=400)

                promocode.title = title

            # check discount
            if discount:
                if discount < 0 or discount > 100:
                    return JsonResponse({"status": False, "message": "Discount must be 0-100"}, status=400)
                
                promocode.discount = discount
            
            # check limit
            if limit:
                if limit < 1 or limit > 1000:
                    return JsonResponse({"status": False, "message": "Limit must be 1-1000"}, status=400)

                promocode.limit = limit
            
            # check end_date
            if end_date:
                tomorrow = date.today() + timedelta(days=1)
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                
                if end_date.date() < tomorrow:
                    return JsonResponse({"status": False, "message": "Finish date must be not earlier then tomorrow!"}, status=400)
                event = promocode.related_event
                if event.end_event_date:
                    if end_date.date() > event.end_event_date.date():
                        return JsonResponse({"status": False, "message": "Finish date must be not later then end event date!"}, status=400)
                else:
                    if end_date.date() > event.start_event_date.date():
                        return JsonResponse({"status": False, "message": "Finish date must be not later then event date!"}, status=400)
                promocode.finish_date = end_date
            else:
                promocode.finish_date = None
            
            if active is not None:
                promocode.active = active
        promocode.save()
        return JsonResponse({"status": True})
    
    
