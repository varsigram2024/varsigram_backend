from rest_framework import serializers
from .models import User, Student, Organization
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.hashers import make_password
from rest_framework_jwt.settings import api_settings


class UserSerializer(serializers.ModelSerializer):
    """ Serializer for user objects """
    class Meta:
        model = User
        fields = ['id', 'email', 'bio', 'is_staff', 'is_deleted']
        read_only_fields = ['is_staff', 'is_deleted']


class StudentRegisterSerializer(serializers.ModelSerializer):
    """ Serializer for student objects """
    user = UserSerializer()

    class Meta:
        model = Student
        fields = ['user', 'name', 'faculty', 'department', 'year', 'religion', 'phone_number', 'sex', 'university']
    
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
        user = self.context['request'].user

        if user.pk != instance.user.pk:
            raise serializers.ValidationError("You do not have permission to update this student")
        
        user_data = validated_data.pop('user', None)
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class OrganizationRegisterSerializer(serializers.ModelSerializer):
    """ Serializer for organization objects (exclusive to admins only)"""
    user = UserSerializer()

    class Meta:
        model = Organization
        fields = ['user', 'organisation_name']
    
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
        fields = ['user', 'organisation_name']
    
    def update(self, instance, validated_data):
        """Update an organization and associated user."""
        user = self.context['request'].user

        if user.pk != instance.user.pk:
            raise serializers.ValidationError("You do not have permission to update this organization")
        
        user_data = validated_data.pop('user', None)
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    """ Serializer for user registration."""
    password = serializers.CharField(write_only=True)
    student = StudentRegisterSerializer(required=False)
    organization = OrganizationRegisterSerializer(required=False)
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['email', 'password', 'bio', 'token', 'student', 'organization']

    def create(self, validated_data):
        """Create a user with hashed password and related student or organization."""
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data, password=password)
        
        # Create the student or organization if provided in the data
        student_data = validated_data.get('student', None)
        organization_data = validated_data.get('organization', None)
        
        if student_data:
            # Register user as a student
            student_serializer = StudentRegisterSerializer(data=student_data)
            if student_serializer.is_valid():
                student_serializer.save(user=user)
            else:
                user.delete()
                raise serializers.ValidationError(student_serializer.errors)
        
        if organization_data:
            # Register user as an organization
            organization_serializer = OrganizationRegisterSerializer(data=organization_data)
            if organization_serializer.is_valid():
                organization_serializer.save(user=user)
            else:
                user.delete()
                raise serializers.ValidationError(organization_serializer.errors)

        return user
    
    def get_token(self, obj):
        """Generate and return JWT token for the user using rest_framework_jwt."""
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        payload = jwt_payload_handler(obj)
        token = jwt_encode_handler(payload)
        return token
    

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
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User does not exist")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user_id = int(urlsafe_base64_decode(data['uid']).decode())
            self.user = User.objects.get(id=user_id)
        except (ValueError, ObjectDoesNotExist):
            raise serializers.ValidationError("Invalid user ID")
        
        try:
            AccessToken(data['token'])
        except Exception:
            raise serializers.ValidationError("Invalid token")
        
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def save(self):
        self.user.password = make_password(self.validated_data['new_password'])
        self.user.save()

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value

class UserSearchSerializer(serializers.Serializer):
    faculty = serializers.CharField(required=False)
    department = serializers.CharField(required=False)

class GoogleInputSerializer(serializers.Serializer):
    code = serializers.CharField(required=False)
    error = serializers.CharField(required=False)
    state = serializers.CharField(required=False)

