from django.urls import path
from .views import (
    UserView, PasswordResetView, PasswordResetConfirmView,
    StudentRegisterView, OrganizationRegisterView, LoginView, 
    ChangePasswordView, StudentProfileView, OrganizationProfileView,
    UserSearchView
)

urlpatterns = [
    path('', UserView.as_view()),
    path('student-register/', StudentRegisterView.as_view(), name='student-register'),
    path('admin/organization-register/', OrganizationRegisterView.as_view(), name='organization-register'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('profile/student/', StudentProfileView.as_view(), name='student-profile'),
    path('profile/organization/', OrganizationProfileView.as_view(), name='organization-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('users/search/', UserSearchView.as_view(), name='search'),
]
