import uuid
import secrets
import string
from django.db import models

class Wall(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    creator_email = models.EmailField()
    # 8-letter unique code (letters only) used as an alternate join identifier
    code = models.CharField(max_length=8, unique=True, db_index=True, editable=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @staticmethod
    def _generate_code(length=8):
        alphabet = string.ascii_uppercase
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def save(self, *args, **kwargs):
        # Ensure a unique 8-letter code is assigned on creation
        if not self.code:
            # Attempt a few times to avoid infinite loops in rare collision cases
            for _ in range(10):
                candidate = self._generate_code(8)
                if not Wall.objects.filter(code=candidate).exists():
                    self.code = candidate
                    break
            else:
                # Fallback: use uuid hex truncated and uppercased if collisions persist
                self.code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

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