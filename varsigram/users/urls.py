from django.urls import path
from .views import (
    UserView, PasswordResetView, PasswordResetConfirmView,
    RegisterView, LoginView, 
    ChangePasswordView, UserProfileView,
    UserSearchView, UserLogout,
    StudentUpdateView, OrganizationUpdateView,
    UserDeactivateView, UserReactivateView,
    VerifyOTPView, SendOTPView,
    CheckUserVerification,
    GetSignedUploadUrlView,
    PublicProfileView,
    GetSignedPostMediaUploadUrlView
)

urlpatterns = [
    path('welcome/', UserView.as_view(), name='welcome'),
    path('register/', RegisterView.as_view(), name='user register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', UserLogout.as_view(), name='logout'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('student/update/', StudentUpdateView.as_view(), name='student-update'),
    path('organization/update/', OrganizationUpdateView.as_view(), name='organization-update'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('users/search/', UserSearchView.as_view(), name='search'),
    path('deactivate/', UserDeactivateView.as_view(), name='user-deactivate'),
    path('reactivate/', UserReactivateView.as_view(), name='user-reactivate'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('check-verification/', CheckUserVerification.as_view(), name='check-verification'),
    path('get-signed-upload-url/', GetSignedUploadUrlView.as_view(), name='get-signed-upload-url'),
    path('profile/<slug:slug>/', PublicProfileView.as_view(), name='public-profile'),
    path('get_post_media_upload_url/', GetSignedPostMediaUploadUrlView.as_view(), name='get_post_media_upload_url'),
]
