# from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Message, User
from rest_framework.exceptions import ValidationError
from .serializer import MessageSerializer

class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)

    def perform_create(self, serializer):
        receiver_id = self.request.data.get('receiver')
        try:
            receiver = User.objects.get(pk=receiver_id)
            serializer.save(sender=self.request.user, receiver=receiver)
        except User.DoesNotExist:
            raise ValidationError("Invalid Receiver ID")

class MessageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(receiver=user)
