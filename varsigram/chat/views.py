# from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Message, User
from rest_framework.exceptions import ValidationError
from .serializer import MessageSerializer
from django.db.models import Q

class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        other_user_id = self.request.query_params.get('other_user')
        if other_user_id:
            try:
                other_user = User.objects.get(pk=other_user_id)
                return Message.objects.filter(
                    Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user)
                ).order_by('date')
            except User.DoesNotExist:
                return Message.objects.none()
        return Message.objects.filter(Q(sender=user) | Q(receiver=user)).order_by('date')

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
