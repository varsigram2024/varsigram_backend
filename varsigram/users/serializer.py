from rest_framework import serializers
from .models import User, Student, Organization
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.hashers import make_password
from django.utils.http import urlsafe_base64_decode
from rest_framework_simplejwt.tokens import AccessToken
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'user_type', 'bio', 'profile_picture']


class StudentRegisterSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Student
        fields = ['user', 'name', 'faculty', 'department', 'matric_number', 'phone_number']
    
    def create(self, validated_data):
        """ Create a new student """
        user_data = validated_data.pop('user')
        user = User.objects.create(**user_data, user_type='student')
        student = Student.objects.create(user=user, **validated_data)
        return student

class OrganizationRegisterSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Organization
        fields = ['user', 'organisation_name']
    
    def create(self, validated_data):
        """ Create a new organization """
        user_data = validated_data.pop('user')
        user = User.objects.create(**user_data, user_type='organization')
        organization = Organization.objects.create(user=user, **validated_data)
        return organization

class LoginSerializer(TokenObtainPairSerializer):
        @classmethod
        def get_token(cls, user):
            token = super().get_token(user)
            token['email'] = user.email
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


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'user_type', 'bio', 'profile_picture']

class StudentUpdateSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer()

    class Meta:
        model = Student
        fields = ['user', 'name', 'faculty', 'department', 'matric_number', 'phone_number']
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.user.save()
        instance.save()
        return instance

class OrganizationUpdateSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer()

    class Meta:
        model = Organization
        fields = ['user', 'organisation_name']
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.user.save()
        instance.save()
        return instance

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
