from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser,
    PermissionsMixin
)
from django.db import models
from django.utils import timezone
from uuid import uuid4
from django.core.exceptions import ValidationError

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

class User(AbstractBaseUser, PermissionsMixin):
    """ Base User Model """
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=150)
    bio = models.TextField(blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    # profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # groups = models.ManyToManyField(
    #     'auth.Group',
    #     related_name='baseuser_set',  # Add this line
    #     blank=True,
    #     help_text='The groups this user belongs to.',
    #     verbose_name='groups',
    # )
    # user_permissions = models.ManyToManyField(
    #     'auth.Permission',
    #     related_name='baseuser_set',  # Add this line
    #     blank=True,
    #     help_text='Specific permissions for this user.',
    #     verbose_name='user permissions',
    # )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'password']
    objects = UserManager()

    def __str__(self):
        return self.email
    
    def delete(self, using=None, keep_parents=False):
        """ Soft delete the user """
        self.is_deleted = True
        self.save(using=using)  
    
    def restore(self):
        """ Restore the user """
        self.is_deleted = False
        self.save()

class Student(models.Model):
    """ Model for Student related to User """
    SEX_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='student')
    name = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    university = models.CharField(max_length=50)
    year = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=20)
    religion = models.CharField(max_length=20)
    sex = models.CharField(max_length=20, choices=SEX_CHOICES)

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

    def __str__(self):
        return f"{self.user.email} (Organization)"
    
    def save(self, *args, **kwargs):
        """ Validate that a user cannot be both a student and an organization"""
        if hasattr(self.user, 'student'):
            raise ValidationError("A user cannot be both a student and an organization.")
        super().save(*args, **kwargs)
