from django.db import models
from atlima_django.common.models import Organizer
from atlima_django.sport_events.models import Event
from asgiref.sync import async_to_sync
from atlima_django.users.models import User
from channels.layers import get_channel_layer


class PostAttachment(models.Model):
    event = models.ForeignKey(
        to=Event,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    photo = models.ImageField(
        upload_to="post_images",
        null=True,
        blank=True,
    )
    blurhash = models.CharField(
        max_length=4096, blank=True, null=True
    )
    document = models.FileField(
        upload_to="post_documents",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"post id{str(self.id)}"


class Post(models.Model):
    """
    Модель поста для ленты (Главная страница)
    """

    content = models.TextField()

    creator_user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        verbose_name="Creator",
        related_name="post_creator",
        null=True,
        blank=True,
    )

    creator_organizer = models.ForeignKey(
        to=Organizer,
        on_delete=models.CASCADE,
        verbose_name="Creator (organizer)",
        related_name="post_creator_organizer",
        null=True,
        blank=True,
    )

    post_attachments = models.ManyToManyField(
        PostAttachment
    )
    likes = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    reposted = models.PositiveIntegerField(
        default=0
    )
    comments = models.PositiveIntegerField(
        default=0
    )

    repost = models.ForeignKey(
        to="self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    # мета
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.content[:100]}-{str(self.created)}"


class PostLike(models.Model):
    """Информация о лайках в разрезе пользователя"""

    post = models.ForeignKey(
        to=Post, on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        to=User, on_delete=models.CASCADE
    )
    created = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if not self.pk:
            post = self.post
            post.likes += 1
            post.save()
        super(PostLike, self).save(
            *args, **kwargs
        )

    def delete(self, *args, **kwargs):
        post = self.post
        post.likes -= 1
        post.save()
        super(PostLike, self).delete()

    def __str__(self):
        return f"user{self.user.id}-post{self.post.id}"

    class Meta:
        unique_together = ["post", "user"]


class PostView(models.Model):
    """Информация о просмотрах в разрезе пользователя"""

    post = models.ForeignKey(
        to=Post, on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if not self.pk:
            post = self.post
            post.views += 1
            post.save()

            channel_layer = get_channel_layer()
            data = {
                "id": self.post.id,
                "likes": self.post.likes,
                "views": self.post.views,
            }
            async_to_sync(
                channel_layer.group_send
            )(
                "broadcast",
                {
                    "event": "post_view_update",
                    "type": "populate.likes",
                    "data": data,
                },
            )

        super(PostView, self).save(
            *args, **kwargs
        )

    def delete(self, *args, **kwargs):
        post = self.post
        post.views -= 1
        post.save()

        super(PostView, self).delete()

        channel_layer = get_channel_layer()
        data = {
            "id": self.post.id,
            "likes": self.post.likes,
            "views": self.post.views,
        }
        async_to_sync(channel_layer.group_send)(
            "broadcast",
            {
                "event": "post_view_update",
                "type": "populate.likes",
                "data": data,
            },
        )

    def __str__(self):
        return f"user{self.user}-post"

    class Meta:
        unique_together = ["post", "user"]


class Comment(models.Model):
    commentable_id = (
        models.PositiveBigIntegerField()
    )
    comment_id = models.PositiveBigIntegerField()
    user = models.ForeignKey(
        to=User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_index=True,
    )
    message = models.TextField()
    reply_id = models.PositiveBigIntegerField(
        null=True, blank=True
    )

    deleted = models.BooleanField(default=False)
    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"comment_{self.user.last_name}_{self.user.first_name}_{str(self.comment_id)}"
        else:
            return f"comment_anon_{str(self.comment_id)}"

    def save(self, *args, **kwargs):
        if not self.pk:
            post = Post.objects.filter(
                id=self.commentable_id
            ).first()
            post.comments += 1
            post.save()

            channel_layer = get_channel_layer()
            data = {
                "id": self.commentable_id,
                "comments": post.comments,
            }
            async_to_sync(
                channel_layer.group_send
            )(
                "broadcast",
                {
                    "event": "post_commented",
                    "type": "send.comment",
                    "data": data,
                },
            )
        super(Comment, self).save(*args, **kwargs)
