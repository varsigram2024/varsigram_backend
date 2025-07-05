from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics
# from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound
from rest_framework_jwt.settings import api_settings
from .models import User, Student, Organization
from postMang.models import Follow
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
from postMang.apps import get_firebase_storage_client
# from django.core.exceptions import PermissionDenied, AuthenticationFailed
from django.conf import settings
# from auth.oauth import (
#     GoogleSdkLoginFlowService,
# )
from auth.jwt import JWTAuthentication
from django.contrib.auth import authenticate, login, logout
from .tasks import send_otp_email
# from firebase_admin import storage
from datetime import timedelta
import os
from uuid import uuid4
from django.contrib.contenttypes.models import ContentType
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
        # print(f"Request Data from Frontend {request.data}")
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
            # print(f"Serializer => {serializer.errors}")
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

    def patch(self, request, *args, **kwargs):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudentUpdateSerializer(student, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationUpdateView(generics.GenericAPIView):
    """View for updating an organization's profile."""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def patch(self, request, *args, **kwargs):
        try:
            organization = Organization.objects.get(user=request.user)
        except Organization.DoesNotExist:
            return Response({"detail": "Organization profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrganizationUpdateSerializer(organization, data=request.data, context={'request': request}, partial=True)
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

class UserSearchView(generics.RetrieveAPIView): # Changed to RetrieveAPIView as per template
    """
    View for searching users (students or organizations) using Django ORM,
    following the structure of the provided template.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs): # Changed to get method as per template
        # Retrieve search parameters from query string
        search_type = request.GET.get('type')
        faculty = request.GET.get('faculty')      # Use request.GET.get() for consistency with template
        department = request.GET.get('department')

        # print(faculty, department, search_type) # Debugging output
        
        users_found = [] # List to hold the formatted user data

        # --- Input Validation and ORM Query Construction ---
        
        if not search_type:
            # Explicitly require 'type' parameter if not defaulting to 'all users'
            return Response(
                data={'message': 'Missing "type" parameter. Please specify "student" or "organization".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if search_type == 'student':
            # Stricter validation for student search: require faculty or department
            if not faculty and not department:
                return Response(
                    data={'message': 'For search type "student", provide at least "faculty" or "department" parameter.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            queryset = User.objects.filter(student__isnull=False) # Start with all users who are students

            if faculty:
                # __icontains maps to ILIKE in PostgreSQL, which is case-insensitive and safe
                queryset = queryset.filter(student__faculty__icontains=faculty)
            if department:
                queryset = queryset.filter(student__department__icontains=department)
            
            # Populate results for students
            for user in queryset:
                student = user.student # Access the related student object
                users_found.append({
                    'email': user.email,
                    'faculty': student.faculty,
                    'department': student.department,
                    'name': student.name,
                    'display_name_slug': student.display_name_slug
                })

        elif search_type == 'organization':
            # For organization search, you might add further required params here if needed
            # For now, we'll return all organizations if no other filters are applied
            
            queryset = User.objects.filter(organization__isnull=False) # Start with all users who are organizations

            # Example: Add organization-specific filtering if desired
            # org_name = request.GET.get('org_name')
            # if org_name:
            #     queryset = queryset.filter(organization__organization_name__icontains=org_name)

            # Populate results for organizations
            for user in queryset:
                organization = user.organization # Access the related organization object
                users_found.append({
                    'email': user.email,
                    'organization_name': organization.organization_name,
                    'display_name_slug': organization.display_name_slug,
                })
        else:
            # Handle invalid search_type
            return Response(
                data={'message': 'Invalid "type" parameter. Must be "student" or "organization".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Return the collected user data
        # JsonResponse is good, but DRF's Response is more integrated and flexible
        return Response(users_found, status=status.HTTP_200_OK)
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
    authentication_classes = [JWTAuthentication]
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
    authentication_classes = [JWTAuthentication]
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
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user
        if user.is_verified:
            return Response({"message": "User is verified."}, status=status.HTTP_200_OK)
        return Response({"message": "User is not verified."}, status=status.HTTP_400_BAD_REQUEST)


class GetSignedUploadUrlView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        file_name = request.data.get('file_name')
        content_type = request.data.get('content_type') # e.g., 'image/jpeg'

        if not file_name or not content_type:
            return Response(
                {"error": "Both 'file_name' and 'content_type' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate content_type if you have specific allowed types
        allowed_content_types = ['image/jpeg', 'image/png'] # Customize
        if content_type not in allowed_content_types:
            return Response(
                {"error": f"Unsupported content type: {content_type}. Allowed types are: {', '.join(allowed_content_types)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Determine the current user (Student or Organization)
        user = request.user
        profile_type = None
        user_id = None
        
        # This logic needs to match how your custom User model is linked to Student/Organization
        # Assuming request.user is your custom User model (e.g., users.User)
        # and it has related_name accessors like user.student_profile or user.organization_profile
        
        try:
            student_profile = Student.objects.get(user=user)
            user_id = student_profile.user.id # Or user.id if Student/Organization IS the user model
            profile_type = 'student'
        except Student.DoesNotExist:
            try:
                organization_profile = Organization.objects.get(user=user)
                user_id = organization_profile.user.id # Or user.id
                profile_type = 'organization'
            except Organization.DoesNotExist:
                return Response(
                    {"error": "User profile (Student or Organization) not found."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not user_id:
             return Response(
                {"error": "Could not determine user ID for profile path."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Generate a unique filename to prevent collisions and simplify updates
        # Get file extension safely
        _, file_extension = os.path.splitext(file_name)
        unique_filename = f"{uuid4()}{file_extension}"
        
        # Define the storage path in your bucket
        # e.g., 'profile_pictures/<user_id>/<unique_filename>'
        # Or 'organization_logos/<org_id>/<unique_filename>' etc.
        # For simplicity, let's use a single path for now
        destination_path = f"profile_pictures/{user_id}/{unique_filename}"
        
        try:
            # Get the default bucket associated with the initialized Firebase App
            # This relies on 'storageBucket' being set during initialize_app in apps.py
            bucket = get_firebase_storage_client() 
            blob = bucket.blob(destination_path)

            # Generate the signed URL for PUT operation
            # The 'Content-Type' must be specified here and must match the client's upload header
            upload_url = blob.generate_signed_url(
                version='v4',
                expiration=timedelta(minutes=15),  # URL valid for 15 minutes
                method='PUT',
                content_type=content_type, # CRITICAL: This must match frontend's Content-Type header
            )

            # Optionally, construct a public download URL if you want to store it
            public_download_url = (
                f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
                f"{destination_path.replace('/', '%2F')}?alt=media"
            )

            return Response({
                "upload_url": upload_url,
                "file_path": destination_path,  # Path in the bucket
                "public_download_url": public_download_url  # <-- This is what frontend should save
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # print(f"Error generating signed URL: {e}")
            return Response(
                {"error": f"Could not generate signed URL: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublicProfileView(APIView):
    """
    Retrieve a user's public profile by display_name_slug.
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        user = request.user if request.user.is_authenticated else None
        is_following = False

        # Try to find a student with this slug
        student = Student.objects.filter(display_name_slug=slug).first()
        if student:
            student_ct = ContentType.objects.get(model='student')
            # Followers: anyone following this student
            followers_count = Follow.objects.filter(
                followee_content_type=student_ct,
                followee_object_id=student.id
            ).count()
            # Following: how many profiles this student is following
            following_count = Follow.objects.filter(
                follower_content_type=student_ct,
                follower_object_id=student.id
            ).count()

            # Check if current user is following this student
            if user and hasattr(user, 'student'):
                follow_exists = Follow.objects.filter(
                    follower_content_type=student_ct,
                    follower_object_id=user.student.id,
                    followee_content_type=student_ct,
                    followee_object_id=student.id
                ).exists()
                is_following = follow_exists
            serializer = StudentProfileSerializer(student)
            return Response({
                "profile_type": "student",
                "profile": serializer.data,
                "is_following": is_following,
                "followers_count": followers_count,
                "following_count": following_count,
            })

        # Try to find an organization with this slug
        organization = Organization.objects.filter(display_name_slug=slug).first()
        if organization:
            student_ct = ContentType.objects.get(model='student')
            org_ct = ContentType.objects.get(model='organization')
            # Followers: anyone following this organization
            followers_count = Follow.objects.filter(
                followee_content_type=org_ct,
                followee_object_id=organization.id
            ).count()
            # Following: how many profiles this organization is following (if orgs can follow)
            following_count = Follow.objects.filter(
                follower_content_type=org_ct,
                follower_object_id=organization.id
            ).count()

            if user and hasattr(user, 'student'):
                follow_exists = Follow.objects.filter(
                    follower_content_type=student_ct,
                    follower_object_id=user.student.id,
                    followee_content_type=org_ct,
                    followee_object_id=organization.id
                ).exists()
                is_following = follow_exists
            serializer = OrganizationProfileSerializer(organization)
            return Response({
                "profile_type": "organization",
                "profile": serializer.data,
                "is_following": is_following,
                "followers_count": followers_count,
                "following_count": following_count,
            })

        return Response({"detail": "Profile not found."}, status=404)

class GetSignedPostMediaUploadUrlView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        file_name = request.data.get('file_name')
        content_type = request.data.get('content_type')

        if not file_name or not content_type:
            return Response(
                {"error": "Both 'file_name' and 'content_type' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        allowed_content_types = [
            'image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/quicktime'
        ]
        if content_type not in allowed_content_types:
            return Response(
                {"error": f"Unsupported content type: {content_type}. Allowed types are: {', '.join(allowed_content_types)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        user_id = None
        try:
            student_profile = Student.objects.get(user=user)
            user_id = student_profile.user.id
        except Student.DoesNotExist:
            try:
                organization_profile = Organization.objects.get(user=user)
                user_id = organization_profile.user.id
            except Organization.DoesNotExist:
                return Response(
                    {"error": "User profile (Student or Organization) not found."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not user_id:
            return Response(
                {"error": "Could not determine user ID for post media path."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        _, file_extension = os.path.splitext(file_name)
        unique_filename = f"{uuid4()}{file_extension}"
        destination_path = f"post_media/{user_id}/{unique_filename}"

        try:
            bucket = get_firebase_storage_client()
            blob = bucket.blob(destination_path)
            upload_url = blob.generate_signed_url(
                version='v4',
                expiration=timedelta(minutes=15),
                method='PUT',
                content_type=content_type,
            )
            public_download_url = (
                f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/"
                f"{destination_path.replace('/', '%2F')}?alt=media"
            )
            return Response({
                "upload_url": upload_url,
                "file_path": destination_path,
                "public_download_url": public_download_url
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # print(f"Error generating signed URL: {e}")
            return Response(
                {"error": f"Could not generate signed URL: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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