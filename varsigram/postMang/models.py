from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone
from users.models import Student, Organization
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


User = get_user_model()
# class Post(models.Model):
#     """ Model to represent the post """
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
#     content = models.TextField()
#     image = models.ImageField(upload_to='post_images/', blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     slug = models.SlugField(unique=True, blank=True, null=True)
    
#     def save(self, *args, **kwargs):
#         if not self.slug:
#             base_slug = slugify(self.content[:50]) #Slugify content
#             timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
#             unique_slug = f"{base_slug}-{timestamp}"
#             self.slug = unique_slug

#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.user}: {self.content[:30]}"

# class Like(models.Model):
#     """ Model to represent the likes on the post """
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
#     created_at = models.DateTimeField(auto_now_add=True)

# class Comment(models.Model):
#     """ Model to represent the comments on the post """
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
#     content = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)

# class Share(models.Model):
#     """ Model to represent the shared post """
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
#     shared_at = models.DateTimeField(auto_now_add=True)#

#     def __str__(self):
#         return f"{self.user} shared {self.post.user}'s post"

class Follow(models.Model):
    follower_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='follower_type', null=True, blank=True)
    follower_object_id = models.PositiveIntegerField(null=True, blank=True)
    follower = GenericForeignKey('follower_content_type', 'follower_object_id')

    followee_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='followee_type', null=True, blank=True)
    followee_object_id = models.PositiveIntegerField(null=True, blank=True)
    followee = GenericForeignKey('followee_content_type', 'followee_object_id')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ('follower_content_type', 'follower_object_id', 'followee_content_type', 'followee_object_id'),
        )
