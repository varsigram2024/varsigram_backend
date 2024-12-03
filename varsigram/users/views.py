from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from rest_framework_jwt.settings import api_settings
# import requests
# import os

from .models import User
from .serializer import ( 
    StudentSerializer, OrganizationSerializer,
    UserSearchSerializer, UserSerializer, GoogleInputSerializer,
    PasswordResetConfirmSerializer, PasswordResetSerializer, ChangePasswordSerializer,
    RegisterSerializer, LoginSerializer, StudentUpdateSerializer, OrganizationUpdateSerializer
)
from django.core.mail import send_mail
from .utils import generate_jwt_token
# from django.core.exceptions import PermissionDenied, AuthenticationFailed
from django.conf import settings
from auth.oauth import (
    GoogleSdkLoginFlowService,
)
# import urllib.parse

# Create your views here.
class UserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response("Hello, World!")

class RegisterView(generics.GenericAPIView):
    """ View to register users (students or organizations). """
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        """ Handle the POST request for user registration. """
        # Validate and create user, student, or organization
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = serializer.get_token(user)
            return Response({
                'message': 'User registered successfully',
                'token': token
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(generics.GenericAPIView):
    """ View to log in a user and return a JWT token. """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        """ Handle POST request for user login. """
        # Deserialize the data and validate user credentials
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            # Generate JWT token
            token = self.get_jwt_token(user)
            return Response({
                'message': 'Login successful',
                'token': token
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_jwt_token(self, user):
        """ Generate a JWT token for the user. """
        return generate_jwt_token(user)


class PasswordResetView(APIView):
    """ Send password reset link to user email """
    permission_classes = []
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)

            # Generate token
            refresh = RefreshToken.for_user(user)
            token = str(refresh.access_token)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

            send_mail(
                "Password Reset Request",
                f"Click the link to reset your password: {reset_link}",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            return Response({"message": "Password reset link sent successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    """ Reset user password """
    permission_classes = []
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    """ Change user password """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password changed successfully!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StudentProfileView(APIView):
    """ View and update student profile """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        student = request.user.student
        serializer = StudentUpdateSerializer(student)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        student = request.user.student
        serializer = StudentUpdateSerializer(student, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        student = request.user.student
        serializer = StudentUpdateSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrganizationProfileView(APIView):
    """ View and update organization profile """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        organization = request.user.organization
        serializer = OrganizationUpdateSerializer(organization)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        # Ensure the user is an organization (i.e., has an Organization profile)
        try:
            organization = request.user.organization
        except ObjectDoesNotExist:
            return Response({"error": "You do not have an organization profile."}, status=status.HTTP_404_NOT_FOUND)

        # Update the organization profile using the serializer
        serializer = OrganizationUpdateSerializer(organization, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Organization profile updated successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        # Ensures the user is an organization
        try:
            organization = request.user.organization
        except ObjectDoesNotExist:
            return Response({"error": "You do not have an organization profile."}, status=status.HTTP_404_NOT_FOUND)

        # Updates the organization profile using the serializer
        serializer = OrganizationUpdateSerializer(organization, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Organization profile updated successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Retrieve the search parameters
        faculty = request.query_params.get('faculty', None)
        department = request.query_params.get('department', None)
        search_type = request.query_params.get('type', None)  # This will specify if we're searching for 'students' or 'organizations'

        # Start with the base query for filtering the Users
        users_query = User.objects.all()

        # If searching for Students:
        if search_type == 'student':
            # Filter by faculty and department if specified and if the user is a student
            if faculty:
                users_query = users_query.filter(student__faculty__icontains=faculty)
            if department:
                users_query = users_query.filter(student__department__icontains=department)

            # Serialize the student data
            user_data = []
            for user in users_query:
                if hasattr(user, 'student'):
                    student = user.student
                    user_data.append({
                        'email': user.email,
                        'faculty': student.faculty,
                        'department': student.department,
                        'name': student.name,
                        'matric_number': student.matric_number,
                    })

        # If searching for Organizations:
        elif search_type == 'organization':
            # Filter only users who are organizations
            users_query = users_query.filter(organization__isnull=False)

            # Serialize the organization data
            user_data = []
            for user in users_query:
                if hasattr(user, 'organization'):
                    organization = user.organization
                    user_data.append({
                        'email': user.email,
                        'organization_name': organization.organization_name,
                    })
        
        # If no 'type' is specified, return all users (students + organizations)
        else:
            user_data = []
            for user in users_query:
                if hasattr(user, 'student'):
                    student = user.student
                    user_data.append({
                        'email': user.email,
                        'faculty': student.faculty,
                        'department': student.department,
                        'name': student.name,
                        'matric_number': student.matric_number,
                    })
                elif hasattr(user, 'organization'):
                    organization = user.organization
                    user_data.append({
                        'email': user.email,
                        'organization_name': organization.organization_name,
                    })

        return Response(user_data, status=status.HTTP_200_OK)


class PublicApi(APIView):
    authentication_classes = ()
    permission_classes = ()


class GoogleLoginRedirectApi(PublicApi):
    def get(self, request, *args, **kwargs):
        google_login_flow = GoogleSdkLoginFlowService()

        authorization_url, state = google_login_flow.get_authorization_url()

        request.session["google_oauth2_state"] = state

        return redirect(authorization_url)

class GoogleLoginApi(PublicApi):
    def get(self, request, *args, **kwargs):
        input_serializer = GoogleInputSerializer(data=request.GET)
        input_serializer.is_valid(raise_exception=True)

        validated_data = input_serializer.validated_data

        code = validated_data.get("code")
        error = validated_data.get("error")
        state = validated_data.get("state")

        if error is not None:
            return Response(
                {"error": error},
                status=status.HTTP_400_BAD_REQUEST
            )

        if code is None or state is None:
            return Response(
                {"error": "Code and state are required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        session_state = request.session.get("google_oauth2_state")

        if session_state is None:
            return Response(
                {"error": "CSRF check failed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        del request.session["google_oauth2_state"]

        if state != session_state:
            return Response(
                {"error": "CSRF check failed."},
                status=status.HTTP_400_BAD_REQUEST
            )