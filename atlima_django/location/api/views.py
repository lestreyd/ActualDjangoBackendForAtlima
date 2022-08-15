from rest_framework.views import APIView
from django.http import JsonResponse
from atlima_django.location.models import (CountryTranslation,
                                           RegionTranslation,
                                           CityTranslation,
                                           Country, 
                                           Region, 
                                           City)
from atlima_django.location.api.serializers import CountrySerializer
from rest_framework import filters
from rest_framework import generics
from django.db.models import Q, CharField
from django.db.models.functions import Lower
from django.core.exceptions import ObjectDoesNotExist


# получить страну по идентификатору
class CountryManager(APIView):
    
    def get(self, request, country_id):
        country = Country.objects.get(id = country_id)
        serializer = CountrySerializer
        serialized = serializer(country)
        
        return JsonResponse(serialized.data)
    
    
# поиск страны по названию. Поскольку используются
# переводимые модели, Django-Parler создаёт новые
# модели. Например, для страны это CountryTranslation
# а для события EventTranslation
class CountrySearch(APIView):
    
    def _get_serialized_countries(self, founded):
        # собрать из перевода и инстанса список стран
        countries = []
        for country in founded:
            country_details = Country.objects.get(id=country.id)
            country = {
                "id": country.id,
                "title": country.title,
                "alpha2": country_details.alpha2,
                "alpha3": country_details.alpha3,
                "iso": country_details.iso
            }
            countries.append(country)
        return countries
    
    def get(self, request):
        
        # получаем имя из запроса
        CharField.register_lookup(Lower, 'lower')
        # name = request.GET.get('name')
        name = request.data.get('search-term', None)
        
        if name is not None:
            name = name.lower()
        else:
            countries = self._get_founded_country_array(
                founded = Country.objects.all()
            )
            return JsonResponse(countries, safe = False)
        # ищем страны с вхождением
        countries = []
        founded = CountryTranslation.objects.filter(
            title__lower__icontains=name
        ).all()
        # если нашли, проходимся и забираем
        if founded:
            countries = self._get_serialized_countries(founded)
        
        return JsonResponse(countries, safe = False)
    
    
# поиск региона по названию. такой же как по стране
# поиск идёт по переведённой модели
# здесь не используется сериализатор
class RegionSearch(APIView):
    
    def _get_serialized_regions(self, founded):
        regions = []
        for region_titles in founded:
            region_instance = Region.objects.get(
                titles__title__iexact=region_titles.title
            )
            region = {
                "id": region_titles.id,
                "title": region_titles.title,
                "code": region_instance.code,
                "country": 
                    {
                        "id": region_instance.country.id,
                        "title": region_instance.country.title
                    }
                }
            regions.append(region)
        return regions
    
    def get(self, request):
        # получаем имя из запроса
        CharField.register_lookup(Lower, 'lower')
        name = request.data.get('search-term', None)
        if name is not None:
            name.lower()
        else:
            regions = self._get_serialized_regions(
                founded = Region.objects.all()
            )
            return JsonResponse(regions, safe=False)
        # ищем страны с вхождением
        founded = RegionTranslation.objects.filter(
            title__lower__icontains=name
        ).all()
        # если нашли, проходимся и забираем
        regions = []
        if founded:
            regions = self._get_serialized_regions(
                founded = founded
            )
        return JsonResponse(regions, safe = False)
    
# поиск города по названию
# проводится по переведённой модели
class CitySearch(APIView):
    
    def _get_serialized_cities(self, founded):
        
        cities = []
        for city_title in founded:
            city_instance = City.objects.get(
                titles__title__iexact=city_title.title
            )
            city = {
                "id": city_instance.id,
                "title": city_instance.title,
                "region":{
                    "id": city_instance.region.id,
                    "title": city_instance.region.title,
                    "code": city_instance.region.code,
                    "country":{
                            "id": city_instance.region.country.id,
                            "title": city_instance.region.country.title,
                            "alpha2": city_instance.region.country.alpha2
                        }
                    },
                }
            cities.append(city)
        return cities
    
    def get(self, request):
        # получаем имя из запроса
        CharField.register_lookup(Lower, 'lower')
        name = request.data.get('search-term', None)
        
        if name is not None:
            name.lower()
        else:
            cities = self._get_serialized_cities(
                founded = City.objects.all()
            )
        # ищем страны с вхождением
        founded = CityTranslation.objects.filter(
            title__lower__icontains=name
        ).all()
        # если нашли, проходимся и забираем
        cities = []
        if founded:
            cities = self._get_serialized_cities(
                founded = founded
            )
        return JsonResponse(cities, safe = False)
    
    
class CityAPI(APIView):
    def get(self, request, city_id):
        if request.version == "1.0" or request.version is None:

            try:
                city = City.objects.get(id=city_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"city_id": ["city not found"]}}, status=404)

            serializer = self.get_serializer_class(request)
            serialized = serializer(city)
            data = serialized.data

            return JsonResponse(data)
        else:
            try:
                city = City.objects.get(id=city_id)
            except ObjectDoesNotExist:
                return JsonResponse({"status": False, "errors": {"city_id": ["city not found"]}}, status=404)

            serializer = self.get_serializer_class(request)
            serialized = serializer(city)
            data = serialized.data

            return JsonResponse(data)


