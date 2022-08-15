from atlima_django.money.models import Currency, PromoCode
from atlima_django.sport_events.models import Slot
from rest_framework import serializers
from atlima_django.money.models import PriceConfiguration



# сериализатор валюты
class CurrencySerializer(serializers.ModelSerializer):

    class Meta:
        model = Currency
        fields = ('id', 'digital_code', 'code', 'title')


# сериализатор промокодов
class PromocodeSerializer(serializers.ModelSerializer):
    # In promocode serializer we can get used parameter
    # this param shows how many timwa promocode was used.
    
    used = serializers.SerializerMethodField('get_used')

    def get_used(self, obj):
        used = Slot.objects.filter(paid=True, id=obj.id)
        return used

    class Meta:
        model = PromoCode
        fields = '__all__'
        
        
# сериализатор ценовой конфигурации для события 
class PriceOptionSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    title = serializers.SerializerMethodField('get_title')
    
    class Meta:
        model = PriceConfiguration
        fields = '__all__'