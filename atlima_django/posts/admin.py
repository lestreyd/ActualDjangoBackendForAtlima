from django.contrib import admin
from .models import Post, PostAttachment

# встроенная форма для прикрепления файлов к
# посту в ленте. 
class PostAttachmentInline(admin.TabularInline):
    model = PostAttachment
    extra = 1
    min_num = 1
    max_num = 100
    
    
# управление постави в ленте
class PostAdmin(admin.ModelAdmin):

    inlines = [PostAttachmentInline]
    list_display = ('id', "content", 'creator_user', 'creator_organizer', 'likes', 'views', 'reposted', 'repost_id', 'created', 'updated')

    class Meta:
        model = Post
        fields = '__all__'
        
        
