from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils import timezone
from .models import Student, Organization

@receiver(pre_save, sender=Student)
def create_student_slug(sender, instance, **kwargs):
    if not instance.display_name_slug:
        base_slug = slugify(instance.name)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f")  # Include microseconds for higher precision
        instance.display_name_slug = f"{base_slug}-{instance.user.id}-{timestamp}"

@receiver(pre_save, sender=Organization)
def create_organization_slug(sender, instance, **kwargs):
    if not instance.display_name_slug:
        base_slug = slugify(instance.organization_name)
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S%f") # Include microseconds for higher precision
        instance.display_name_slug = f"{base_slug}-{instance.user.id}-{timestamp}"