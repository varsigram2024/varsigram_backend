from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """ Base User Model """
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('organization', 'Organization'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'user_type', 'password']

    def __str__(self):
        return self.email

class Student(models.Model):
    """ Model for Student related to User """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student')
    name = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    matric_number = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.email} (Student)"

class Organization(models.Model):
    """ Model for Organization related to User """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='organization')
    organisation_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.email} (Organization)"
