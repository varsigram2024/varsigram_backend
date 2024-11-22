from django.urls import path
from .views import UserView, PasswordResetView, PasswordResetConfirmView

urlpatterns = [
    path('', UserView.as_view()),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm')
]
