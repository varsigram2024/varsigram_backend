from rest_framework import serializers
from .models import User, Student, Organization
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import PasswordResetTokenGenerator
# from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.hashers import make_password
# from rest_framework_jwt.settings import api_settings
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
# from django.contrib.sites.shortcuts import get_current_site
# from .utils import generate_jwt_token
# from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
import os
from django.utils.timezone import now
from .tasks import send_reset_email
from django.utils.translation import gettext_lazy as _
from firebase_admin import auth


class UserSerializer(serializers.ModelSerializer):
    """ Serializer for user objects """

    display_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'email', 'display_name', 'bio', 'is_deleted', 'is_verified', 'profile_pic_url']
        read_only_fields = ['id', 'is_deleted', 'is_verified']

    def get_display_name(self, obj):
        if obj.get_display_name():
            return obj.get_display_name()
        return obj.email

class StudentRegisterSerializer(serializers.ModelSerializer):
    """ Serializer for student objects """

    class Meta:
        model = Student
        fields = ['name', 'faculty', 'department', 'year', 'religion', 'phone_number', 'sex', 'university', 'date_of_birth']
    
    def create(self, validated_data):
        """ Create a new student """
        user_data = validated_data.pop('user')
        password = user_data.pop('password', None)
        user = User.objects.create_user(**user_data, password=password)
        student = Student.objects.create(user=user, **validated_data)
        return student

class StudentUpdateSerializer(serializers.ModelSerializer):
    """ Serializer for updating student objects """
    user = UserSerializer(partial=True)

    class Meta:
        model = Student
        fields = ['user', 'name', 'faculty', 'department', 'year', 'religion', 'phone_number', 'sex', 'university', 'date_of_birth']

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
        fields = ['organization_name', 'exclusive']
    
    def create(self, validated_data):
        """ Create a new organization """
        user_data = validated_data.pop('user')
        password = user_data.pop('password', None)
        user = User.objects.create_user(**user_data, password=password)
        organization = Organization.objects.create(user=user, **validated_data)
        return organization

class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """ Serializer for updating organization objects """
    user = UserSerializer(partial=True)

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
    # Change 'token' to 'tokens' as we return both access and refresh
    tokens = serializers.SerializerMethodField() # Changed from 'token' to 'tokens'

    class Meta:
        model = User
        fields = ['email', 'password', 'bio', 'tokens', 'student', 'organization'] # Changed 'token' to 'tokens'

    def validate(self, data):
        # ... (your existing validation logic remains unchanged) ...
        if data.get('student') and data.get('organization'):
            raise serializers.ValidationError("You cannot register as both a student and an organization.")
        if not data.get('student') and not data.get('organization'):
            raise serializers.ValidationError("You must provide either a student or an organization.")
        return data
    
    def create(self, validated_data):
        """Create a User and associated Student or Organization."""
        student_data = validated_data.pop('student', None)
        organization_data = validated_data.pop('organization', None)
        password = validated_data.pop('password')

        user = User.objects.create(
            **validated_data,
            password=make_password(password)
        )

        if student_data:
            student = Student.objects.create(user=user, **student_data)
            user.student = student

        if organization_data:
            organization = Organization.objects.create(user=user, **organization_data)
            user.organization = organization

        user.save()
        return user


    # Returns both access and refresh tokens
    def get_tokens(self, user): # Changed method name to get_tokens
        refresh = RefreshToken.for_user(user)
        response_data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        try:
            custom_claims = {
                'is_verified': user.is_verified,
            }
            firebase_custom_token = auth.create_custom_token(str(user.id), custom_claims).decode('utf-8')
            response_data['firebase_custom_token'] = firebase_custom_token
        except Exception as e:
            print(f"Error generating Firebase custom token: {e}")
        
        return response_data


    

class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    tokens = serializers.SerializerMethodField() # Changed from 'token' to 'tokens'

    def validate(self, data):
        """Validate user credentials."""
        user = authenticate(email=data['email'], password=data['password'])
        if not user or user.is_deleted:
            raise serializers.ValidationError("Invalid credentials or inactive account.")
        data['user'] = user # Store user in validated_data for get_tokens
        return data

    # Returns both access and refresh tokens
    def get_tokens(self, obj): # Changed method name to get_tokens
        # obj here is the validated_data from the serializer, which contains 'user'
        user = obj['user']
        refresh = RefreshToken.for_user(user)
        response_data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        try:
            custom_claims = {
                'is_verified': user.is_verified,
            }
            firebase_custom_token = auth.create_custom_token(str(user.id), custom_claims).decode('utf-8')
            response_data['firebase_custom_token'] = firebase_custom_token
        except Exception as e:
            print(f"Error generating Firebase custom token: {e}")
        
        return response_data


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """ Check if the user exists """
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User does not exist")
        return value

    def save(self, request): # Keep request argument, it's good practice for context
        """ Generates a reset link and sends an email using Django's token """
        email = self.validated_data['email']
        user = User.objects.get(email=email)


        # Generate token using Django's PasswordResetTokenGenerator
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)


        uid = urlsafe_base64_encode(force_bytes(user.id))
        # Ensure DOMAIN is set in your environment variables for production/staging
        frontend_url = f"{os.getenv('FRONTEND_DOMAIN')}/reset-password" # Use os.getenv and a more descriptive env var name

        reset_link = f"{frontend_url}?uid={uid}&token={token}"
        # Assuming send_reset_email is a Celery task or similar
        # Ensure your email template mentions that this link is time-sensitive.
        # You might pass the request for site name in email context
        send_reset_email.delay(email, reset_link) # Pass token and uid as well if your email needs them separately


class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    # Add uid and token as fields that the serializer expects from the client
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)


    def validate(self, data):
        """ Validates the token, UID, and password match. """
        new_password = data['new_password']
        confirm_password = data['confirm_password']
        uidb64 = data['uid']
        token = data['token']

        if new_password != confirm_password:
            raise serializers.ValidationError({"new_password": "Passwords do not match"})

        try:
            # Decode UID and get user
            user_id = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'uid': _('Invalid User ID or reset link.')})

        # Validate the token using Django's PasswordResetTokenGenerator
        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            raise serializers.ValidationError({'token': _('Invalid or expired token.')})

        # Optional: Add Django's password validation rules (if configured in AUTH_PASSWORD_VALIDATORS)
        # from django.contrib.auth.password_validation import validate_password
        # try:
        #     validate_password(new_password, user=user)
        # except Exception as e:
        #     raise serializers.ValidationError({'new_password': list(e.messages)})


        self.user = user # Store user for use in save method
        return data

    def save(self):
        """ Update the user's password """
        # self.user is set in the validate method
        self.user.set_password(self.validated_data['new_password']) # Use set_password to hash
        self.user.save()
        return self.user # Return the user instance

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
        fields = ['user', 'id', 'name', 'display_name_slug','faculty', 'department', 'year', 'religion', 'phone_number', 'sex', 'university', 'date_of_birth']

class OrganizationProfileSerializer(serializers.ModelSerializer):
    """Serializer for retrieving organization profiles."""
    user = UserSerializer()

    class Meta:
        model = Organization
        fields = ['user', 'id', 'organization_name', 'display_name_slug', 'exclusive']

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

