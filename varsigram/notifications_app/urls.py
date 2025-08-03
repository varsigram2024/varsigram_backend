from django.urls import path
from .views import RegisterDeviceView, UnregisterDeviceView


app_name = 'notification'

urlpatterns = [
    path('register/', RegisterDeviceView.as_view(), name='register_device'),
    path('unregister/<str:registration_id>/', UnregisterDeviceView.as_view(), name='unregister_device'),
]
