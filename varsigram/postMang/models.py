from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils import timezone
from users.models import Student, Organization
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator


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

class RewardPointTransaction(models.Model):
    """
    Records points given to a Firestore Post. 
    The post's author is stored locally for easy calculation.
    """
    # Giver: The user submitting the points
    giver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='given_rewards'
    )
    
    # Firestore Link: The ID of the post in the Firestore database
    firestore_post_id = models.CharField(
        max_length=100, 
        db_index=True,
        verbose_name="Firestore Post ID"
    )
    
    # Denormalization: The author of the post (local User FK)
    # This is critical for efficient, private point totaling.
    post_author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_rewards',
        verbose_name="Post Author"
    )
    
    points = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5) # Max points per transaction is 5
        ],
        help_text="Points given (1 to 5)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Reward Point Transaction"
        # Optional: You might add a UniqueConstraint here if a user can only reward a post once:
        constraints = [
            models.UniqueConstraint(fields=['giver', 'firestore_post_id'], name='unique_reward_per_post')
        ]


    def __str__(self):

        if hasattr(self.giver, 'student'):
            username = self.giver.student.name
        elif hasattr(self.giver, 'organization'):
            username = self.giver.organization.organization_name
        else:
            username = self.giver.email
        return (f"{username} gave {self.points} pts "
                f"to Post ID {self.firestore_post_id} (Author: {self.post_author.username})")