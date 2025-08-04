from django.urls import path
from .views import (
    RegisterDeviceView, UnregisterDeviceView,
    NotificationListView, NotificationMarkReadView,
    UnreadNotificationCountView
)

app_name = 'notification'

urlpatterns = [
    # --- Device Registration and Unregistration ---
    path('register/', RegisterDeviceView.as_view(), name='register_device'),
    path('unregister/<str:registration_id>/', UnregisterDeviceView.as_view(), name='unregister_device'),

    # --- Notification Management ---
    path('', NotificationListView.as_view(), name='notification-list'), # List all notifications
    path('<int:pk>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('unread_count/', UnreadNotificationCountView.as_view(), name='unread-notification-count'),
]
