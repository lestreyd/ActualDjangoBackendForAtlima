from rest_framework import serializers
from atlima_django.posts.models import PostLike
from  atlima_django.users.models import User
import urllib
import blurhash
from atlima_django.posts.models import PostAttachment
from django.conf import settings
from atlima_django.common.api.serializers import OrganizerMenuSerializer
from atlima_django.sport_events.api.serializers import EventMenuSerializer
from atlima_django.posts.models import Post


# сериализатор прикрепления к посту
# в этом массиве содержатся все фото, которые приаттачены к
# текущему посту
class PostAttachmentPhotoSerializer(serializers.ModelSerializer):

    photo = serializers.SerializerMethodField('get_photo')
    blurhash = serializers.SerializerMethodField('get_blurhash')

    def get_blurhash(self, obj):
        if obj.photo:
            url = urllib.unquote(obj.photo.url)
            if obj.blurhash is None:
                media = '/'.join(settings.MEDIA_ROOT.split('/')[:len(settings.MEDIA_ROOT.split('/'))-1])
                path = media + url
                with open (path, 'rb') as f:
                    bh = blurhash.encode(f, x_components=4, y_components=3)
                obj.blurhash = bh
                obj.save()
            else:
                bh = obj.blurhash
            return bh
        return None 

    def get_photo(self, obj):
        if obj.photo:
            return obj.photo.url
        else:
            return None

    class Meta:
        model = PostAttachment
        exclude = ['event', 'document', 'related_post']


# сериализатор документа в прикреплении поста
class PostAttachmentDocumentSerializer(serializers.ModelSerializer):

    document = serializers.SerializerMethodField('get_document')

    def get_document(self, obj):
        if obj.document:
            return obj.document.url
        else:
            return None

    class Meta:
        model = PostAttachment
        exclude = ['event', 'photo', 'related_post']


# сериализатор поста
class PostSerializer(serializers.ModelSerializer):
    # user = UserSerializer(source='creator_user')
    id = serializers.IntegerField(read_only=True)
    user = serializers.SerializerMethodField('get_user_credentials')
    organizer = serializers.SerializerMethodField('get_organizer_creator')
    attachments = serializers.SerializerMethodField('get_post_attachments')
    editors = serializers.SerializerMethodField('get_post_editors')
    liked = serializers.SerializerMethodField('get_my_like')

    def _user(self, obj):
        request = self.context.get('request', None)
        if request:
            return request.user

    def get_my_like(self, obj):
        user = self._user(obj)
        if type(user) == User:
            like = PostLike.objects.filter(user=user, post=obj)        
            if like:
                return True
        return False

    def get_organizer_creator(self, obj):
        serializer = OrganizerMenuSerializer
        request = self.context.get('request', None)
        if obj.creator_organizer is not None:
            serialized = serializer(obj.creator_organizer, context={'request': request})
            # return obj.creator_organizer.id
            return serialized.data
        else:
            return None

    def get_user_credentials(self, obj):
        result = {}
        result['user_id'] = obj.creator_user.id
        result['username'] = f"{obj.creator_user.first_name} {obj.creator_user.last_name}"
        if obj.creator_user.profile_photo:
            result['photo'] = obj.creator_user.profile_photo.url
        else:
            result['photo'] = None
        return result

    def get_post_editors(self, obj):
        """все, кто может редактировать пост"""
        result = []

        # если организатор непустой, то создано от его имени
        if obj.creator_organizer is not None:
            editors = User.objects.filter(organizer_record=obj.creator_organizer).all()
            for editor in editors:
                result.append(editor.profile_record.user.id)
            result.append(obj.creator_user.id)
        else:
        # если не от имени организатора, то от имени пользователя
            editor = obj.creator_user
            result.append(editor.id)
        return result


    def get_post_attachments(self, obj):
        attachments = PostAttachment.objects.filter(related_post=obj)

        result = {}
        events = []
        photos = []
        docs = []
        
        for attach in attachments:
            
            if attach.event:
                serializer = EventMenuSerializer
                serialized = serializer(attach.event, context={"request": self.context['request']})
                events.append(serialized.data)

            if attach.photo:
                serializer = PostAttachmentPhotoSerializer
                serialized = serializer(attach)
                photos.append(serialized.data)

            if attach.document:
                serializer = PostAttachmentDocumentSerializer
                serialized = serializer(attach)
                docs.append(serialized.data)

        result['events'] = events
        result['photos'] = photos
        result['documents'] = docs
        
        return result

    class Meta:
        model = Post
        exclude = ['creator_user', 'creator_organizer']
        
        
        
