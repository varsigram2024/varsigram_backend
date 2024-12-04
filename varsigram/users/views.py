from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound
from django.shortcuts import redirect
from rest_framework_jwt.settings import api_settings

from .models import User, Student, Organization
from .serializer import ( 
    UserSearchSerializer, UserSerializer, GoogleInputSerializer,
    PasswordResetConfirmSerializer, PasswordResetSerializer, ChangePasswordSerializer,
    RegisterSerializer, LoginSerializer, StudentUpdateSerializer, OrganizationUpdateSerializer,
    OrganizationProfileSerializer, StudentProfileSerializer,
    UserDeactivateSerializer, UserReactivateSerializer
)
from django.core.mail import send_mail
from .utils import generate_jwt_token
# from django.core.exceptions import PermissionDenied, AuthenticationFailed
from django.conf import settings
from auth.oauth import (
    GoogleSdkLoginFlowService,
)
from auth.jwt import JWTAuthentication
from django.contrib.auth import authenticate, login, logout
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
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        """ Handle POST request for user login. """
        # Deserialize the data and validate user credentials
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
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

class UserLogout(APIView):
    """ logout user """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logout(request)
        msg = {'message': 'Logged Out Successfully'}
        return Response(data=msg, status=status.HTTP_200_OK)

class PasswordResetView(APIView):
    """ Send password reset link to user email """
    permission_classes = []
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(request=request)
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

    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password changed successfully!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StudentUpdateView(APIView):
    """View for updating a student's profile."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def put(self, request, *args, **kwargs):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudentUpdateSerializer(student, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationUpdateView(APIView):
    """View for updating an organization's profile."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def put(self, request, *args, **kwargs):
        try:
            organization = Organization.objects.get(user=request.user)
        except Organization.DoesNotExist:
            return Response({"detail": "Organization profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrganizationUpdateSerializer(organization, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.GenericAPIView):
    """ View for retrieving the current user's profile """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """Retrieve the authenticated user's profile."""
        user = request.user
        try:
            if hasattr(user, 'student'):
                serializer = StudentProfileSerializer(user.student)
                profile_type = "student"
            elif hasattr(user, 'organization'):
                serializer = OrganizationProfileSerializer(user.organization)
                profile_type = "organization"
            else:
                raise NotFound("Profile not found for the current user.")

            return Response(
                {
                    "profile_type": profile_type,
                    "profile": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except NotFound as e:
            raise e

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
                    })
                elif hasattr(user, 'organization'):
                    organization = user.organization
                    user_data.append({
                        'email': user.email,
                        'organization_name': organization.organization_name,
                    })

        return Response(user_data, status=status.HTTP_200_OK)

class UserDeactivateView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        serializer = UserDeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)


        user = request.user
        user.delete()
        return Response(
            {"message": "Account deactivated successfully"},
            status=status.HTTP_200_OK
        )

class UserReactivateView(APIView):
    """ Reactivate a user account """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        serializer = UserReactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        
        if not user.is_deleted:
            return Response(
                {"message": "Account is already active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.restore()
        return Response(
            {"message": "Account reactivated successfully"},
            status=status.HTTP_200_OK
        )

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
        
        google_login_flow = GoogleSdkLoginFlowService()

        google_tokens = google_login_flow.get_tokens(code=code, state=state)

        id_token_decoded = google_tokens.decode_id_token()
        user_info = google_login_flow.get_user_info(google_tokens=google_tokens)

        user_email = id_token_decoded["email"]
        user = User.objects.filter(email=user_email).first()

        if user is None:
            return Response(
                {"error": f"User with email {user_email} is not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        login(request, user)

        result = {
            "id_token_decoded": id_token_decoded,
            "user_info": user_info,
        }

        return Response(result)