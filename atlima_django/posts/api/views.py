from rest_framework.views import APIView
from django.core.exceptions import ObjectDoesNotExist
from atlima_django.posts.models import Post, PostLike
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from django.http import JsonResponse
from rest_framework.pagination import PageNumberPagination
from atlima_django.posts.api.serializers import PostSerializer
from django.db.models import Q, CharField
from rest_framework.views import generics, APIView
from django.db.models.functions import Lower


class EventPaginator(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class DislikePostManagement(APIView):
    # ПОДСИСТЕМА УПРАВЛЕНИЯ ПОСТАМИ
    authentication_classes = [TokenAuthentication]

    def post(self, request, post_id):
        # LIKE
        user = request.user
        try:
            post = Post.objects.get(id=post_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"post_id": ["not found"]}}, status=404)

        user_like = PostLike.objects.filter(user=user, post=post).first()

        if user_like:
            user_like.delete()
        else:
            return JsonResponse({"status": False, 
                                "errors": {"like": ['you dont like it yet']}}, 
                                status=400)
        
        return JsonResponse({"status": True})


class PostManagement(APIView):

    authentication_classes = [TokenAuthentication]

    def post(self, request, post_id):
        # LIKE
        user = request.user
        try:
            post = Post.objects.get(id=post_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": False, "errors": {"post_id": ["not found"]}}, status=404)

        user_like = PostLike.objects.filter(user=user, post=post).first()

        if user_like is None:
            like = PostLike.objects.create(user=user, post=post)
            like.save()
        else:
            return JsonResponse({"status": False, 
                                "errors": {"like": ['you already like it']}}, 
                                status=400)
        return JsonResponse({"status": True})



class SearchPosts(generics.ListAPIView):
    pagination_class = EventPaginator
    serializer_class = PostSerializer
    
    def get_queryset(self):
        request = self.request
        CharField.register_lookup(Lower, 'lower')
        search_term = request.GET.get('q', None)

        if search_term is not None:
            posts = Post.objects.filter(content__icontains=search_term, active=True).all().order_by('-views', '-likes', 'created')
        else:
            posts = Post.objects.filter(active=True).all().order_by('-views', '-likes', 'created')
        return posts


class MyPosts(generics.ListAPIView):
    pagination_class = EventPaginator
    serializer_class = PostSerializer
    
    def get_queryset(self):
        user = self.request.user
        posts = Post.objects.filter(creator_user=user, active=True).all().order_by('-views', 
                                                                                    '-likes', 
                                                                                    'created')
        return posts




# ПОДСИСТЕМА УЧЁТА ПОСТОВ И ПОИСКА (CHANNELS)
class PostList(generics.ListAPIView):
    serializer_class = PostSerializer
    pagination_class = EventPaginator
    # queryset = Post.objects.filter(active=True).all().order_by('-views', '-likes', '-created')

    def get_queryset(self):
        request = self.request
        if request.version == "1.0" or request.version is None:
            CharField.register_lookup(Lower, 'lower')
            search_term = request.GET.get('q', None)
            
            # import urllib.parser as urllib
            # search_term = urllib.unquote(search_term)

            if search_term is not None:
                posts = Post.objects.filter(content__icontains=search_term, active=True).all().order_by('-created', '-views', '-likes')
            else:
                posts = Post.objects.filter(active=True).all().order_by('-created', '-views', '-likes')
            return posts
        elif request.version == "1.1":
            CharField.register_lookup(Lower, 'lower')
            search_term = request.GET.get('q', None)

            if search_term is not None:
                posts = Post.objects.filter(content__icontains=search_term, active=True).all().order_by('-views', '-likes', 'created')
            else:
                posts = []
            return posts
        else:
            CharField.register_lookup(Lower, 'lower')
            search_term = request.GET.get('q', None)

            if search_term is not None:
                posts = Post.objects.filter(content__icontains=search_term, active=True).all().order_by('-views', '-likes', 'created')
            else:
                posts = Post.objects.filter(active=True).all().order_by('-views', '-likes', 'created')
            return posts


