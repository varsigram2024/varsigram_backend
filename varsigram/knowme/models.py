import uuid
from django.db import models

class Wall(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    creator_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class WallMember(models.Model):
    wall = models.ForeignKey(Wall, on_delete=models.CASCADE, related_name='members')
    full_name = models.CharField(max_length=200)
    contact_info = models.CharField(max_length=255)
    interests = models.TextField()
    # Removed local `photo` ImageField — images are stored in Firebase and `photo_url` keeps the external link
    photo_url = models.URLField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-joined_at']