from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils import timezone
from .models import Student, Organization
from notifications_app.utils import send_push_notification
from django.contrib.auth.models import User

@receiver(pre_save, sender=Student)
def create_student_slug(sender, instance, **kwargs):
    if not instance.display_name_slug:
        base_slug = slugify(instance.name)
        # timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")  # Include microseconds for higher precision
        instance.display_name_slug = f"{base_slug}-{instance.user.id}"

@receiver(pre_save, sender=Organization)
def create_organization_slug(sender, instance, **kwargs):
    if not instance.display_name_slug:
        base_slug = slugify(instance.organization_name)
        # timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f") # Include microseconds for higher precision
        instance.display_name_slug = f"{base_slug}-{instance.user.id}"

@receiver(post_save, sender=User)
def welcome_new_user(sender, instance, created, **kwargs):
    if created:
        # Send a welcome email or notification
        send_push_notification(
            user=instance,
            title="Welcome to Varsigram!",
            body="Thank you for joining Varsigram. We're glad to have you!",
            data={
                "type": "welcome"
            }
        )