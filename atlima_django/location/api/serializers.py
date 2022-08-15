from parler_rest.serializers import TranslatableModelSerializer
from parler_rest.fields import TranslatedFieldsField
from atlima_django.location.models import Country, Region, City
from rest_framework import serializers
        

class CountrySerializer(TranslatableModelSerializer):
    # мультиязычный сериализатор страны
    titles = TranslatedFieldsField(shared_model=Country)
    class Meta:
        model = Country
        fields = ('titles', 'alpha2', 'alpha3', 'location', 'location_precise')
        
        
class RegionSerializer(TranslatableModelSerializer):
    # мультиязычный сериализатор региона
    titles = TranslatedFieldsField(shared_model=Region)
    country = CountrySerializer()
    class Meta:
        model = Region
        fields = ('titles', 'code', 'country')
        

class CitySerializer(TranslatableModelSerializer):
    # мультиязычный сериализатор города
    titles = TranslatedFieldsField(shared_model=City)
    region = RegionSerializer()
    class Meta:
        model = City
        fields = ('titles', 'region')