from rest_framework import serializers
from .models import User, Student, Organization
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.hashers import make_password
from rest_framework_jwt.settings import api_settings
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from .utils import generate_jwt_token
from django.conf import settings
import random
from django.utils.timezone import now
from .tasks import send_reset_email


class UserSerializer(serializers.ModelSerializer):
    """ Serializer for user objects """
    display_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'email', 'display_name', 'bio', 'is_deleted', 'is_verified']
        read_only_fields = ['id', 'is_deleted', 'is_verified']
    
    def get_display_name(self, obj):
        """ Get the display name for the user """
        return str(obj)


class StudentRegisterSerializer(serializers.ModelSerializer):
    """ Serializer for student objects """

    class Meta:
        model = Student
        fields = ['name', 'faculty', 'department', 'year', 'religion', 'phone_number', 'sex', 'university']
    
    def create(self, validated_data):
        """ Create a new student """
        user_data = validated_data.pop('user')
        password = user_data.pop('password', None)
        user = User.objects.create_user(**user_data, password=password)
        student = Student.objects.create(user=user, **validated_data)
        return student

class StudentUpdateSerializer(serializers.ModelSerializer):
    """ Serializer for updating student objects """
    user = UserSerializer()

    class Meta:
        model = Student
        fields = ['user', 'name', 'faculty', 'department', 'year', 'religion', 'phone_number', 'sex', 'university']

    def update(self, instance, validated_data):
        """Update a student and associated user."""
        request_user = self.context['request'].user

        # Ensure the user is the owner of the student profile
        if not instance.user == request_user:
            raise serializers.ValidationError(
                {"detail": "You do not have permission to update this student."}
            )

        # Update user fields if provided
        user_data = validated_data.pop('user', None)
        if user_data:
            for attr, value in user_data.items():
                if getattr(instance.user, attr) != value:  # Update only changed fields
                    setattr(instance.user, attr, value)
            instance.user.save()

        # Update student fields
        for attr, value in validated_data.items():
            if getattr(instance, attr) != value:  # Update only changed fields
                setattr(instance, attr, value)
        instance.save()

        return instance


class OrganizationRegisterSerializer(serializers.ModelSerializer):
    """ Serializer for organization objects (exclusive to admins only)"""

    class Meta:
        model = Organization
        fields = ['organization_name']
    
    def create(self, validated_data):
        """ Create a new organization """
        user_data = validated_data.pop('user')
        password = user_data.pop('password', None)
        user = User.objects.create_user(**user_data, password=password)
        organization = Organization.objects.create(user=user, **validated_data)
        return organization

class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """ Serializer for updating organization objects """
    user = UserSerializer()

    class Meta:
        model = Organization
        fields = ['user', 'organization_name']
    
    def update(self, instance, validated_data):
        """Update an organization and associated user."""
        request_user = self.context['request'].user

        # Ensure the user is the owner of the organization profile
        if not instance.user == request_user:
            raise serializers.ValidationError(
                {"detail": "You do not have permission to update this organization."}
            )

        # Update user fields if provided
        user_data = validated_data.pop('user', None)
        if user_data:
            for attr, value in user_data.items():
                if getattr(instance.user, attr) != value:  # Update only changed fields
                    setattr(instance.user, attr, value)
            instance.user.save()

        # Update organization fields
        for attr, value in validated_data.items():
            if getattr(instance, attr) != value:  # Update only changed fields
                setattr(instance, attr, value)
        instance.save()

        return instance


class RegisterSerializer(serializers.ModelSerializer):
    """ Serializer for user registration."""
    password = serializers.CharField(write_only=True)
    student = StudentRegisterSerializer(required=False, allow_null=True)
    organization = OrganizationRegisterSerializer(required=False, allow_null=True)
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['email', 'password', 'bio', 'token', 'student', 'organization']
    
    def validate(self, data):
        """ Custom validation to ensure that only one of `student` or `organization` is provided. """
        # print("i was called")
        if data.get('student') and data.get('organization'):
            raise serializers.ValidationError("You cannot register as both a student and an organization.")
        if not data.get('student') and not data.get('organization'):
            raise serializers.ValidationError("You must provide either a student or an organization.")
        return data
    
    def create(self, validated_data):
        """Create a User and associated Student or Organization."""
        # print("Was I here???")
        student_data = validated_data.pop('student', None)
        organization_data = validated_data.pop('organization', None)
        password = validated_data.pop('password')

        # print(f"Validated data: {validated_data} === Student data: {student_data}")

        # Create the user
        user = User.objects.create(
            **validated_data,
            password=make_password(password)
        )

        # Create related models
        if student_data:
            student = Student.objects.create(user=user, **student_data)
            user.student = student  # Assign the student instance
        
        if organization_data:
            organization = Organization.objects.create(user=user, **organization_data)
            user.organization = organization  # Assign the organization instance

        user.save()
        return user
    
    def get_token(self, obj):
        """Generate and return JWT token for the user using rest_framework_jwt."""
        return generate_jwt_token(obj)

    

class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    token = serializers.SerializerMethodField()

    def validate(self, data):
        """Validate user credentials."""
        user = authenticate(email=data['email'], password=data['password'])
        if not user or user.is_deleted:
            raise serializers.ValidationError("Invalid credentials or inactive account.")
        data['user'] = user
        return data
    
    def get_token(self, obj):
        """Generate and return JWT token for the user using rest_framework_jwt."""
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(obj['user'])
        token = jwt_encode_handler(payload)
        return token

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """ Check if the user exists """
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User does not exist")
        return value
    
    def save(self, request):
        """ Generates a reset link and sends an email """
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        token = generate_jwt_token(user)
        current_site = get_current_site(request)
        domain = current_site.domain
        uid = urlsafe_base64_encode(force_bytes(user.id))
        reset_link = f"http://{domain}/api/v1/password-reset-confirm/?uid={uid}&token={token}"

        send_reset_email.delay(email, reset_link)


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        """ Validates the token and match the passwords. """
        
        user = self.context['user']
        self.user = user

        # Check if the passwords match
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def save(self):
        """ Update the user's password """
        self.user.password = make_password(self.validated_data['new_password'])
        self.user.save()

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        user = self.context['request'].user

        # Validate old password
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({"old_password": "Old password is incorrect."})

        # Validate new password confirmation
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        return data
    
    def save(self, **kwargs):
        """Save the new password for the user."""
        user = self.context['request'].user
        user.password = make_password(self.validated_data['new_password'])
        user.save()
        return user


class UserSearchSerializer(serializers.Serializer):
    faculty = serializers.CharField(required=False)
    department = serializers.CharField(required=False)

# # class GoogleInputSerializer(serializers.Serializer):
#     code = serializers.CharField(required=False)
#     error = serializers.CharField(required=False)
#     state = serializers.CharField(required=False)

class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for retrieving student profiles."""
    user = UserSerializer()

    class Meta:
        model = Student
        fields = ['user', 'name', 'display_name_slug','faculty', 'department', 'year', 'religion', 'phone_number', 'sex', 'university']

class OrganizationProfileSerializer(serializers.ModelSerializer):
    """Serializer for retrieving organization profiles."""
    user = UserSerializer()

    class Meta:
        model = Organization
        fields = ['user', 'organization_name', 'display_name_slug']

class UserDeactivateSerializer(serializers.Serializer):
    """ Serializer for deactivating a user account """
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """ Validate the user's password """
        user = self.context['request'].user
        if not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid password")
        return data
    
    def save(self):
        """ Deactivate the user account """
        user = self.context['request'].user
        user.is_deleted = True
        user.save()
        return user

class UserReactivateSerializer(serializers.Serializer):
    """ Serializer for reactivating a user account """
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """ Validate the user's password """
        user = self.context['request'].user
        if not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid password")
        return data
    
    def save(self):
        """ Reactivate the user account """
        user = self.context['request'].user
        user.is_deleted = False
        user.save()
        return user

class OTPVerificationSerializer(serializers.Serializer):
    # email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            user = self.context['request'].user
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        if user.otp != data['otp']:
            raise serializers.ValidationError("Invalid OTP.")
        
        if user.otp_expiry < now():
            raise serializers.ValidationError("OTP has expired.")

        return data

class SendOTPSerializer(serializers.Serializer):
    """Serializer for sending OTP to the authenticated user's email."""
    def validate(self, data):
        """Ensure the authenticated user has a valid email."""
        user = self.context['request'].user
        if not user.email:
            raise serializers.ValidationError("User does not have a valid email.")
        return data

