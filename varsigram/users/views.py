from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

from varsigram.users.models import User
from .serializer import StudentRegisterSerializer, OrganizationRegisterSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer, LoginSerializer, ChangePasswordSerializer
from django.core.mail import send_mail

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
            send_mail(
            )