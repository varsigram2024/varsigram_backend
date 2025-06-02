from .models import User, Message
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('id', 'display_name')
    
    def get_display_name(self, obj):
        """ Returns the name of the user """
        return str(obj)

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = Message
        fields = ('id', 'sender', 'receiver', 'content', 'date', 'is_read')