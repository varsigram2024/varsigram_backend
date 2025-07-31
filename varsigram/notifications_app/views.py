from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Device
from .serializers import DeviceSerializer

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
            registration_id=registration_id,
            defaults={
                'user': self.request.user if self.request.user.is_authenticated else None,
                'device_id': device_id,
                'active': True,
            }
        )
        serializer.instance = device
        if created:
            print(f"New device registered: {registration_id}")
        else:
            print(f"Device updated: {registration_id}")


class UnregisterDeviceView(generics.DestroyAPIView):
    queryset = Device.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'registration_id' # Allow deletion by registration_id

    def delete(self, request, *args, **kwargs):
        registration_id = self.kwargs.get(self.lookup_field)
        if not registration_id:
            return Response({"detail": "registration_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(
                registration_id=registration_id,
                user=request.user # Ensure user can only unregister their own device
            )
            device.delete()
            print(f"Device unregistered: {registration_id}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Device.DoesNotExist:
            return Response({"detail": "Device not found or not associated with this user."}, status=status.HTTP_404_NOT_FOUND)
