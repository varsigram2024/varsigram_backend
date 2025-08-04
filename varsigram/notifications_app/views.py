from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Device, Notification
from rest_framework.views import APIView
from .serializers import DeviceSerializer, NotificationSerializer
from django.shortcuts import get_object_or_404

class RegisterDeviceView(generics.CreateAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated] # Or allow unauthenticated if you handle anonymous users

    def perform_create(self, serializer):
        # A user can have multiple devices, so update if exists, otherwise create
        registration_id = self.request.data.get('registration_id')
        device_id = self.request.data.get('device_id') # Optional: for identifying specific devices

        if not registration_id:
            return Response({"detail": "registration_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        device, created = Device.objects.update_or_create(
            user=self.request.user,
            registration_id=registration_id,
            defaults={
                'device_id': device_id,
                'active': True,
            }
        )
        serializer = self.get_serializer(device)
        if created:
            print(f"New device registered for {self.request.user.email}: {registration_id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(f"Device updated/re-activated for {self.request.user.email}: {registration_id}")
            # If the device existed and was just updated, return 200 OK
            return Response(serializer.data, status=status.HTTP_200_OK)


class UnregisterDeviceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, registration_id, *args, **kwargs):
        if not registration_id:
            return Response({"detail": "registration_id is required in URL path."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Only allow a user to deactivate their own device
            device = Device.objects.get(
                user=request.user,
                registration_id=registration_id
            )
            device.active = False # Mark as inactive instead of deleting
            device.save()
            print(f"Device marked inactive: {registration_id} for user {request.user.email}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Device.DoesNotExist:
            return Response({"detail": "Device not found or not associated with this user."}, status=status.HTTP_404_NOT_FOUND)

# --- NEW API Endpoints for Notification Management ---

class NotificationListView(generics.ListAPIView):
    """
    Lists all notifications for the authenticated user.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter notifications to only show those belonging to the current authenticated user
        return Notification.objects.filter(user=self.request.user)

class NotificationMarkReadView(generics.UpdateAPIView):
    """
    Marks a specific notification as read for the authenticated user.
    Only allows PATCH requests.
    """
    queryset = Notification.objects.all() # Base queryset, will be filtered by get_object
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['patch'] # Restrict to PATCH method

    def get_object(self):
        # Ensure the user can only mark their own notifications as read
        # The `pk` comes from the URL (e.g., /notifications/123/mark-read/)
        # Using self.kwargs['pk'] which comes from the URL regex capture.
        obj = get_object_or_404(
            self.get_queryset().filter(user=self.request.user), # Filter by user first for security
            pk=self.kwargs['pk']
        )
        return obj

    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now() # Set read timestamp
            notification.save()
            # Return serializer data if you want the updated notification object
            serializer = self.get_serializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # If already read, still return 200 OK but with a specific message
        return Response({"detail": "Notification was already marked as read."}, status=status.HTTP_200_OK)


class UnreadNotificationCountView(APIView):
    """
    Returns the count of unread notifications for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": unread_count}, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    """
    Marks all unread notifications for the authenticated user as read.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False)
        updated_count = unread_notifications.update(is_read=True, read_at=timezone.now())
        return Response({"message": f"Successfully marked {updated_count} notifications as read."}, status=status.HTTP_200_OK)
