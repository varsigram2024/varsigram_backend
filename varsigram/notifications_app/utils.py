import firebase_admin
from firebase_admin import messaging
from .models import Device
from django.conf import settings

def send_push_notification(user, title, body, data=None):
    """
    Sends a push notification to all active devices of a given user.

    Args:
        user: The Django User instance.
        title (str): The title of the notification.
        body (str): The body/content of the notification.
        data (dict, optional): A dictionary of custom data to send with the notification.
                               This will be available in the app's notification handler.
    """
    if not firebase_admin._apps:
        print("Firebase app not initialized. Cannot send notification.")
        return

    # Get all active registration IDs for the user
    registration_ids = list(Device.objects.filter(user=user, active=True).values_list('registration_id', flat=True))

    if not registration_ids:
        print(f"No active devices found for user {user.email}.")
        return

    # FCM message construction
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data, # Custom data payload
        tokens=registration_ids,
    )

    try:
        response = messaging.send_multicast(message)
        print(f"Successfully sent {response.success_count} messages to user {user.email}.")
        if response.failure_count > 0:
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    print(f"Failed to send message: {resp.exception}")
                    if resp.exception and "NotRegistered" in str(resp.exception):
                        # Deactivate the failed token
                        failed_token = registration_ids[idx]
                        Device.objects.filter(registration_id=failed_token).update(active=False)
    except Exception as e:
        print(f"Error sending push notification to user {user.email}: {e}")
