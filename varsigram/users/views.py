from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework import status, generics
# from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import NotFound
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .models import User, Student, Organization
from postMang.models import Follow
from .serializer import ( 
    # UserSearchSerializer, UserSerializer, GoogleInputSerializer,
    PasswordResetConfirmSerializer, PasswordResetSerializer, ChangePasswordSerializer,
    RegisterSerializer, LoginSerializer, StudentUpdateSerializer, OrganizationUpdateSerializer,
    OrganizationProfileSerializer, StudentProfileSerializer,
    UserDeactivateSerializer, UserReactivateSerializer,
    OTPVerificationSerializer, SendOTPSerializer, SocialLinksSerializer
)
# from django.core.mail import send_mail
from .utils import clean_data
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from postMang.apps import get_firebase_storage_client
from rest_framework_simplejwt.authentication import JWTAuthentication
# from django.core.exceptions import PermissionDenied, AuthenticationFailed
# from django.conf import settings
# from auth.oauth import (
#     GoogleSdkLoginFlowService,
# )
# from auth.jwt import JWTAuthentication
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
        data = clean_data(request.data) # Assuming clean_data function exists elsewhere
        serializer = self.serializer_class(data=data)
        if serializer.is_valid(raise_exception=True): # Use raise_exception=True for cleaner error handling
            user = serializer.save()

            
            # Get both access and refresh tokens from the serializer's method
            tokens = serializer.get_tokens(user)
            

            return Response({
                'message': 'User registered successfully',
                'access': tokens['access'],   # Return the access token
                'refresh': tokens['refresh'], # Return the refresh token
                'firebase_custom_token': tokens['firebase_custom_token'],
            }, status=status.HTTP_201_CREATED)
        # No need for else: return Response(serializer.errors...) because of raise_exception=True


class LoginView(generics.GenericAPIView):
    """ View to log in a user and return a JWT token. """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True): # Use raise_exception=True
            user = serializer.validated_data['user']

            
            # Get both access and refresh tokens from the serializer's method
            tokens = serializer.get_tokens(serializer.validated_data) # Pass validated_data as obj to get_tokens
            

            return Response({
                'message': 'Login successful',
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'firebase_custom_token': tokens['firebase_custom_token'],
            }, status=status.HTTP_200_OK)
        # No need for else: return Response(serializer.errors...)

class UserLogout(APIView):
    """ logout user """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logout(request)
        msg = {'message': 'Logged Out Successfully'}
        return Response(data=msg, status=status.HTTP_200_OK)

# User = get_user_model()


class PasswordResetView(generics.GenericAPIView):
    """ 
    Handles the request to send the password reset link.
    It returns a success response regardless of user existence to prevent enumeration.
    """
    permission_classes = []
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        # 1. Validate the email format and basic data structure
        if serializer.is_valid(raise_exception=True):
            
            # 2. Call the save method, which handles the security check (user exists?) 
            # and sends the email (or fails silently).
            serializer.save(request=request)
            
            # 3. Return a generic success message for security (prevents user enumeration).
            return Response(
                {"message": "If an account with that email exists, a password reset link has been sent."}, 
                status=status.HTTP_200_OK
            )
        # DRF's raise_exception=True already handles 400 errors, but kept for clarity
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(generics.GenericAPIView):
    """ 
    View to handle both link validity check (GET) and password change (POST). 
    """
    permission_classes = [] 
    serializer_class = PasswordResetConfirmSerializer
    User = get_user_model() 

    def get(self, request, *args, **kwargs):
        """ Checks the validity of the UID and Token upon frontend page load. """

        uidb64 = request.query_params.get('uid')
        token = request.query_params.get('token')

        if not uidb64 or not token:
            return Response({"error": "Missing UID or Token in query parameters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = urlsafe_base64_decode(uidb64).decode()
            user = self.User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, self.User.DoesNotExist):
            return Response({"error": "Invalid User ID or Reset Link."}, status=status.HTTP_400_BAD_REQUEST)

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, token):
            return Response({"error": "Invalid or Expired Token."}, status=status.HTTP_400_BAD_REQUEST)

        # Successful validation means the link is live and user can proceed
        return Response({"message": "Validation Successful"}, status=status.HTTP_200_OK)


    def post(self, request, *args, **kwargs):
        """ Sets the new password after successful validation. """
        
        # --- CRITICAL CORRECTION: Inject UID and Token from URL into request data ---
        data = request.data.copy()
        data['uid'] = request.query_params.get('uid')
        data['token'] = request.query_params.get('token')
        
        serializer = self.serializer_class(data=data)
        
        if serializer.is_valid(raise_exception=True):
            serializer.save() 
            return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)

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


class UserSearchPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

class UserSearchView(APIView):
    """
    Search users by name across both Students and Organizations, with pagination.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        query = request.GET.get('query', '').strip()
        faculty = request.GET.get('faculty')
        department = request.GET.get('department')

        if not query and not faculty and not department:
            return Response(
                {"message": 'Provide at least "query", "faculty", or "department".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = []

        # Search Students
        student_qs = Student.objects.all()
        if query:
            student_qs = student_qs.filter(name__icontains=query)
        if faculty:
            student_qs = student_qs.filter(faculty__icontains=faculty)
        if department:
            student_qs = student_qs.filter(department__icontains=department)

        for student in student_qs.select_related('user'):
            results.append({
                'type': 'student',
                'email': student.user.email,
                'faculty': student.faculty,
                'department': student.department,
                'name': student.name,
                'display_name_slug': student.display_name_slug
            })

        # Search Organizations
        org_qs = Organization.objects.all()
        if query:
            org_qs = org_qs.filter(organization_name__icontains=query)

        for org in org_qs.select_related('user'):
            results.append({
                'type': 'organization',
                'email': org.user.email,
                'organization_name': org.organization_name,
                'display_name_slug': org.display_name_slug,
                'exclusive': org.exclusive,
            })

        # Apply pagination
        paginator = UserSearchPagination()
        paginated_results = paginator.paginate_queryset(results, request)
        return paginator.get_paginated_response(paginated_results)

class SocialLinksUpdateView(generics.UpdateAPIView):
    """
    Allows the authenticated user to update their social links directly on their User model.
    PATCH /api/v1/profile/social-links/
    """
    serializer_class = SocialLinksSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch'] # Only allow partial updates

    def get_object(self):
        """Always returns the currently authenticated User instance."""
        return self.request.user

    def perform_update(self, serializer):
        """Saves the updated social links."""
        serializer.save()
        # No extra profile lookup logic needed!


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