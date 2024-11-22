from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

from varsigram.users.models import User
from .serializer import StudentRegisterSerializer, OrganizationRegisterSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer, LoginSerializer, ChangePasswordSerializer
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.
class UserView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        return Response("Hello, World!")

class StudentRegisterView(APIView):
    """ Register a new student """
    permission_classes = []
    serializer_class = StudentRegisterSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({"message": "Student registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrganizationRegisterView(APIView):
    """ Register a new organization """
    permission_classes = []
    serializer_class = OrganizationRegisterSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({"message": "Organization registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(TokenObtainPairView):
    """ Login a user """
    permission_classes = []
    serializer_class = LoginSerializer


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