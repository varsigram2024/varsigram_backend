from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics
# from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound
from rest_framework_jwt.settings import api_settings
from .models import User, Student, Organization
from .serializer import ( 
    # UserSearchSerializer, UserSerializer, GoogleInputSerializer,
    PasswordResetConfirmSerializer, PasswordResetSerializer, ChangePasswordSerializer,
    RegisterSerializer, LoginSerializer, StudentUpdateSerializer, OrganizationUpdateSerializer,
    OrganizationProfileSerializer, StudentProfileSerializer,
    UserDeactivateSerializer, UserReactivateSerializer,
    OTPVerificationSerializer, SendOTPSerializer
)
from django.core.mail import send_mail
from .utils import generate_jwt_token, clean_data
from django.utils.http import urlsafe_base64_decode
# from django.core.exceptions import PermissionDenied, AuthenticationFailed
from django.conf import settings
# from auth.oauth import (
#     GoogleSdkLoginFlowService,
# )
from auth.jwt import JWTAuthentication
from django.contrib.auth import authenticate, login, logout
from .tasks import send_otp_email
from firebase_admin import storage
from datetime import timedelta
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
        print(f"Request Data from Frontend {request.data}")
        # Validate and create user, student, or organization
        data = clean_data(request.data)
        # print(f"Validated Data => {data}")
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            # print("I was valid")
            user = serializer.save()

            if user:
                login(request, user)

                token = serializer.get_token(user)
                return Response({
                    'message': 'User registered successfully',
                    'token': token
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'error': 'An error occurred while registering the user.',
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print(f"Serializer => {serializer.errors}")
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

class PasswordResetView(generics.GenericAPIView):
    """ Send password reset link to user email """
    permission_classes = []
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(request=request)
            return Response({"message": "Password reset link sent successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(generics.GenericAPIView):
    """ Reset user password """
    permission_classes = []
    serializer_class = PasswordResetConfirmSerializer

    def get(self, request, *args, **kwargs):
        uidb64 = request.GET.get('uid')
        token = request.GET.get('token')

        user_id = int(urlsafe_base64_decode(uidb64).decode())
        user = User.objects.get(id=user_id)

        if not user:
            return Response({"error": "Invalid User ID"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
        try:
            jwt_decode_handler(token)
        except Exception:
            return Response({"error": "Invalid Token"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"message": "Validation Successful"}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        uidb64 = request.GET.get('uid')
        user_id = int(urlsafe_base64_decode(uidb64).decode())
        user = User.objects.get(id=user_id)

        serializer = self.serializer_class(data=request.data, context={'user': user})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(generics.GenericAPIView):
    """ Change user password """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password changed successfully!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StudentUpdateView(generics.GenericAPIView):
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


class OrganizationUpdateView(generics.GenericAPIView):
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

class UserSearchView(generics.GenericAPIView):
    """ View for searching users """
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
                        'display_name_slug': organization.display_name_slug,
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
                        'display_name_slug': organization.display_name_slug,
                    })

        return Response(user_data, status=status.HTTP_200_OK)

class UserDeactivateView(generics.GenericAPIView):
    """ Deactivate a user account """
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

class UserReactivateView(generics.GenericAPIView):
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

class SendOTPView(generics.GenericAPIView):
    """ Send OTP to user email """
    permission_classes = [IsAuthenticated]
    serializer_class = SendOTPSerializer

    def post(self, request):
        """ Handles OTP sending for authenticated user. """
        serializer = SendOTPSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        user.generate_otp()
        
        # Send OTP via Celery task
        send_otp_email.delay(user.email, user.otp)
        
        return Response({"message": "OTP sent successfully."}, status=status.HTTP_200_OK)

class VerifyOTPView(generics.GenericAPIView):
    """ Verify OTP for user """
    permission_classes = [IsAuthenticated]
    serializer_class = OTPVerificationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Mark user as verified
            user = request.user
            user.otp = None  # Clear OTP after successful verification
            user.otp_expiration = None
            user.is_verified = True  # Verifies the user
            user.save()
            return Response({"message": "OTP verified successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CheckUserVerification(APIView):
    """ Check if the user is verified """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_verified:
            return Response({"message": "User is verified."}, status=status.HTTP_200_OK)
        return Response({"message": "User is not verified."}, status=status.HTTP_400_BAD_REQUEST)


class GetSignedUploadUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Validate input: file_name, content_type
        # You might want to get the original file name and content type from the frontend
        # For simplicity, let's assume it's passed in the request body
        file_name = request.data.get('file_name')
        content_type = request.data.get('content_type', 'application/octet-stream')

        if not file_name:
            return Response({"error": "file_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate a unique path for the profile picture
        # It's good practice to ensure uniqueness and use the Django user ID
        django_user_id = str(request.user.id)
        unique_filename = f"{django_user_id}_{file_name}" # You might add a timestamp/UUID here too
        storage_path = f"profile_pictures/{django_user_id}/{unique_filename}"

        try:
            bucket = storage.bucket() # Assumes default bucket is initialized
            blob = bucket.blob(storage_path)

            # Generate a signed URL that allows a PUT request for 15 minutes
            upload_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=15),
                method="PUT",
                content_type=content_type, # Ensure this matches what frontend sends
            )
            
            return Response({
                "upload_url": upload_url,
                "file_path": storage_path # Optional: return path for frontend to construct public URL later
            })
        except Exception as e:
            # Log the error carefully, avoid exposing sensitive details
            return Response({"error": f"Could not generate signed URL: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PublicProfileView(APIView):
    """
    Retrieve a user's public profile by display_name_slug.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        # Try to find a student with this slug
        student = Student.objects.filter(display_name_slug=slug).first()
        if student:
            serializer = StudentProfileSerializer(student)
            return Response({"profile_type": "student", "profile": serializer.data})

        # Try to find an organization with this slug
        organization = Organization.objects.filter(display_name_slug=slug).first()
        if organization:
            serializer = OrganizationProfileSerializer(organization)
            return Response({"profile_type": "organization", "profile": serializer.data})

        return Response({"detail": "Profile not found."}, status=404)

# class PublicApi(APIView):
#     authentication_classes = ()
#     permission_classes = ()


# class GoogleLoginRedirectApi(PublicApi):
#     def get(self, request, *args, **kwargs):
#         google_login_flow = GoogleSdkLoginFlowService()

#         authorization_url, state = google_login_flow.get_authorization_url()

#         request.session["google_oauth2_state"] = state

#         return redirect(authorization_url)

# class GoogleLoginApi(PublicApi):
#     def get(self, request, *args, **kwargs):
#         input_serializer = GoogleInputSerializer(data=request.GET)
#         input_serializer.is_valid(raise_exception=True)

#         validated_data = input_serializer.validated_data

#         code = validated_data.get("code")
#         error = validated_data.get("error")
#         state = validated_data.get("state")

#         if error is not None:
#             return Response(
#                 {"error": error},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         if code is None or state is None:
#             return Response(
#                 {"error": "Code and state are required."}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         session_state = request.session.get("google_oauth2_state")

#         if session_state is None:
#             return Response(
#                 {"error": "CSRF check failed."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         del request.session["google_oauth2_state"]

#         if state != session_state:
#             return Response(
#                 {"error": "CSRF check failed."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         google_login_flow = GoogleSdkLoginFlowService()

#         google_tokens = google_login_flow.get_tokens(code=code, state=state)

#         id_token_decoded = google_tokens.decode_id_token()
#         user_info = google_login_flow.get_user_info(google_tokens=google_tokens)

#         user_email = id_token_decoded["email"]
#         user = User.objects.filter(email=user_email).first()

#         if user is None:
#             return Response(
#                 {"error": f"User with email {user_email} is not found."},
#                 status=status.HTTP_404_NOT_FOUND
#             )

#         login(request, user)

#         result = {
#             "id_token_decoded": id_token_decoded,
#             "user_info": user_info,
#         }

#         return Response(result)