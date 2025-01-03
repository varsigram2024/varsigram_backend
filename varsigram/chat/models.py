from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

class Message(models.Model):
    """ Messaging Model """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receiver')
    content = models.CharField(max_length=2000)
    date = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"

    
