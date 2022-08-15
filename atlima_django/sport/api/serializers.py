from rest_framework import serializers
from parler_rest.serializers import TranslatableModelSerializer
from parler_rest.fields import TranslatedFieldsField
from sport.models import Sport


# переводимый сериализатор вида спорта
class SportSerializer(TranslatableModelSerializer):
    id = serializers.IntegerField(source='sport_content.id')
    text = TranslatedFieldsField(shared_model=Sport)
    title = serializers.CharField()
    description = serializers.CharField()
    avatar = serializers.SerializerMethodField(source="image")
    slug = serializers.CharField()
    site = serializers.CharField()


# сериализаторы видов спорта
class SportTypeSerializerv2(serializers.ModelSerializer):

    title = serializers.SerializerMethodField('get_titles')
    description = serializers.SerializerMethodField('get_descriptions')
    avatar = serializers.SerializerMethodField('get_avatar')

    class Meta:
        model = Sport
        exclude = ['created', 'updated', 'owner']

    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.sport_image.url
        return None


# сериализатор вида спорта
class SportTypeSerializerv3(TranslatableModelSerializer):

    id = serializers.IntegerField(read_only=True)
    title = TranslatedFieldsField(shared_model=Sport)
    desciption = TranslatedFieldsField(shared_model=Sport)
    sport_administrators = serializers.SerializerMethodField('get_sport_admins')

    def _user(self, obj):
        request = self.context.get('request', None)
        if request:
            return request.user

    def get_avatar(self, obj):
        if obj.avatar is not None:
            return obj.avatar.sport_image.url
        return None

    def get_sport_description(self, obj):
        sport_content = self.get_sport_content(obj)
        sport_description = sport_content.description if sport_content is not None else "-"
        return sport_description
    
    def get_sport_admins(self, obj):
        # TODO сделать здесь получение админов по ролям
        return None

    class Meta:
        model = Sport
        exclude = ['created', 'updated', 'owner',]