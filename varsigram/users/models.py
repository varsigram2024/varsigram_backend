from django.contrib.auth.models import AbstractUser
from django.db import models

class SoftDeletedManager(models.Manager):
    """ Custom manager to exclude soft-deleted objects. """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class BaseUser(AbstractUser):
    """ Base User Model """
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='baseuser_set',  # Add this line
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='baseuser_set',  # Add this line
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'password']
    objects = SoftDeletedManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.email
    
    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save()
    
    def restore(self):
        self.is_deleted = False
        self.save()

class Student(models.Model):
    """ Model for Student related to User """
    user = models.OneToOneField(BaseUser, on_delete=models.CASCADE, related_name='student')
    name = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    matric_number = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.email} (Student)"

class Organization(models.Model):
    """ Model for Organization related to User """
    user = models.OneToOneField(BaseUser, on_delete=models.CASCADE, related_name='organization')
    organization_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.email} (Organization)"
