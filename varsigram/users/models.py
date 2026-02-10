from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser,
    PermissionsMixin
)
from django.db import models
from django.utils import timezone
from uuid import uuid4
import random
from django.core.exceptions import ValidationError
from django.db.models import Sum

class UserManager(BaseUserManager):
    """ Custom manager to exclude soft-deleted objects. and create user """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def create_user(self, email, password=None, **extra_fields):
        """ Creates and saves a User with the given email and password. """
        if not email:
            raise ValueError('User must have an email address')
        
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
            )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def all_with_deleted(self):
        """ Returns all users including soft-deleted users """
        return super().get_queryset()
    
    def create_superuser(self, email, password=None, **extra_fields):
        """ Creates and saves a superuser with the given email and password. """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

    def hard_delete_user(self, user_or_id_or_email):
        """
        Permanently remove a user and related objects. Accepts a User instance, primary key (int), or email (str).
        Returns True if a user was found and deleted, False otherwise.
        """
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()

        if isinstance(user_or_id_or_email, UserModel):
            user = user_or_id_or_email
        elif isinstance(user_or_id_or_email, int):
            user = self.all_with_deleted().filter(pk=user_or_id_or_email).first()
        else:
            user = self.all_with_deleted().filter(email=user_or_id_or_email).first()

        if user:
            user.hard_delete()
            return True
        return False

class User(AbstractBaseUser, PermissionsMixin):
    """ Base User Model """
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=150)
    # username = models.CharField(max_length=150, unique=True, default='default_username')
    bio = models.TextField(blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    profile_pic_url = models.URLField(max_length=500, blank=True, null=True, 
                                      help_text="URL to the user's profile picture in Firebase Storage.")
    linkedin_url = models.URLField(max_length=200, blank=True, null=True)
    instagram_url = models.URLField(max_length=200, blank=True, null=True)
    twitter_url = models.URLField(max_length=200, blank=True, null=True)
    portfolio_url = models.URLField(max_length=200, blank=True, null=True)
    whatsapp_url = models.URLField(max_length=200, blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expiry = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['password']
    objects = UserManager()

    def __str__(self):
        try:
            return self.student.name
        except Student.DoesNotExist:
            try:
                return self.organization.organization_name
            except Organization.DoesNotExist:
                return self.email
    
    def get_display_name(self):
        """ Returns the name of the user """
        try:
            return self.student.name
        except Student.DoesNotExist:
            try:
                return self.organization.organization_name
            except Organization.DoesNotExist:
                return self.email
    
    def delete(self, using=None, keep_parents=False):
        """ Soft delete the user """
        self.is_deleted = True
        self.save(using=using)  
    
    def restore(self):
        """ Restore the user """
        self.is_deleted = False
        self.save()
    
    def generate_otp(self):
        """ Generate OTP and set the expiry time """
        self.otp = f"{random.randint(100000, 999999)}"
        self.otp_expiry = timezone.now() + timezone.timedelta(minutes=10)
        self.save()
    
    @property
    def total_received_points(self):
        """ 
        Calculates the total points the user has received across all their posts.
        This uses the reverse relation 'received_rewards'.
        """
        # The author of the post is the current user (self)
        return self.received_rewards.aggregate(
            total=Sum('points')
        )['total'] or 0

    def hard_delete(self, using=None, keep_parents=False):
        """
        Permanently delete the user and related objects. This bypasses soft-delete and is irreversible.

        Steps taken:
        - Remove Student/Organization profiles attached to the user (they use PROTECT on delete)
        - Remove Follow entries that reference those profiles
        - Remove reward transactions, messages, devices, and notifications tied to this user
        - Finally delete the user row from the database
        """
        # Import locally to avoid circular imports at module load time
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Q

        # Related models
        try:
            from postMang.models import RewardPointTransaction, Follow
        except Exception:
            RewardPointTransaction = None
            Follow = None
        try:
            from chat.models import Message
        except Exception:
            Message = None
        try:
            from notifications_app.models import Device, Notification
        except Exception:
            Device = None
            Notification = None

        # Delete student/org profiles first (they protect the user on delete)
        try:
            student = getattr(self, 'student', None)
            if student is not None:
                student.delete()
        except Exception:
            pass

        try:
            organization = getattr(self, 'organization', None)
            if organization is not None:
                organization.delete()
        except Exception:
            pass

        # Clean up Follow entries referencing the user's student/org records
        if Follow is not None:
            try:
                if student is not None:
                    ct = ContentType.objects.get_for_model(student.__class__)
                    Follow.objects.filter(
                        Q(follower_content_type=ct, follower_object_id=student.pk) |
                        Q(followee_content_type=ct, followee_object_id=student.pk)
                    ).delete()
                if organization is not None:
                    ct = ContentType.objects.get_for_model(organization.__class__)
                    Follow.objects.filter(
                        Q(follower_content_type=ct, follower_object_id=organization.pk) |
                        Q(followee_content_type=ct, followee_object_id=organization.pk)
                    ).delete()
            except Exception:
                pass

        # Delete reward transactions where this user was giver or post_author
        if RewardPointTransaction is not None:
            try:
                RewardPointTransaction.objects.filter(Q(giver=self) | Q(post_author=self)).delete()
            except Exception:
                pass

        # Delete chat messages where user was sender or receiver
        if Message is not None:
            try:
                Message.objects.filter(Q(sender=self) | Q(receiver=self)).delete()
            except Exception:
                pass

        # Delete devices and notifications belonging to user
        if Device is not None:
            try:
                Device.objects.filter(user=self).delete()
            except Exception:
                pass
        if Notification is not None:
            try:
                Notification.objects.filter(user=self).delete()
            except Exception:
                pass

        # NOTE: If you store profile pictures in Firebase Storage, you may want to remove them here.
        # Consider adding an explicit helper to remove storage objects using your Firebase client.

        # Finally remove the user row itself
        super(User, self).delete(using=using, keep_parents=keep_parents)


class Student(models.Model):
    """ Model for Student related to User """
    # SEX_CHOICES = [
    #     ('Male', 'Male'),
    #     ('Female', 'Female'),
    #     ('Other', 'Other'),
    # ]
    # RELIGION_CHOICES = [
    #     ('Christianity', 'Christianity'),
    #     ('Islam', 'Islam'),
    #     ('Other', 'Other'),
    # ]
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='student')
    name = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    university = models.CharField(max_length=100)
    year = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    religion = models.CharField(max_length=20)
    sex = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    display_name_slug = models.SlugField(unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} (Student)"
    
    def save(self, *args, **kwargs):
        """ Validate that a user cannot be both a student and an organization"""
        if hasattr(self.user, 'organization'):
            raise ValidationError("A user cannot be both a student and an organization.")
        super().save(*args, **kwargs)


class Organization(models.Model):
    """ Model for Organization related to User """
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='organization')
    organization_name = models.CharField(max_length=100)
    display_name_slug = models.SlugField(unique=True, blank=True, null=True)
    exclusive = models.BooleanField(default=False, 
                                  help_text="If True, all students must see and follow this organization.")

    def __str__(self):
        return f"{self.user.email} (Organization)"
    
    def save(self, *args, **kwargs):
        """ Validate that a user cannot be both a student and an organization"""
        if hasattr(self.user, 'student'):
            raise ValidationError("A user cannot be both a student and an organization.")
        super().save(*args, **kwargs)
