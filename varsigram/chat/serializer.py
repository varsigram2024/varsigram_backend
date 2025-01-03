from .models import User, Message
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email')

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = Message
        fields = ('id', 'sender', 'receiver', 'content', 'date', 'is_read')