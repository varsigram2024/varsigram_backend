from rest_framework import serializers
from .models import Device

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['registration_id', 'device_id', 'active']
        read_only_fields = ['active'] # Active is set by the backend on registration
