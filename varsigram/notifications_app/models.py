from django.db import models
from django.conf import settings

class Device(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices',
        blank=True,
        null=True, # Allow anonymous devices if needed
    )
    registration_id = models.CharField(max_length=255, unique=True, help_text="FCM device registration token")
    device_id = models.CharField(max_length=255, blank=True, null=True, unique=True,
                                 help_text="Unique device identifier (e.g., UUID for mobile app)")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Device"
        verbose_name_plural = "Devices"
        unique_together = ('user', 'registration_id') # A user can have multiple devices, but a token is unique

    def __str__(self):
        return f"Device for {self.user.email if self.user else 'Anonymous'} ({self.registration_id[:10]}...)"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(blank=True, null=True, help_text="Custom data payload for the notification")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True) # When the notification was marked as read

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at'] # Order by most recent first

    def __str__(self):
        return f"Notification for {self.user.email}: {self.title} ({'Read' if self.is_read else 'Unread'})"

