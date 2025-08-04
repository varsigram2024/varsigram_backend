# notifications_app/serializers.py
from rest_framework import serializers
from .models import Device, Notification

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'registration_id', 'device_id', 'active', 'created_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'active']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'data', 'is_read', 'created_at', 'read_at']
        read_only_fields = ['id', 'user', 'created_at', 'read_at'] # is_read can be updated by PATCH
