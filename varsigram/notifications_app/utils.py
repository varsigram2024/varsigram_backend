import firebase_admin
from firebase_admin import messaging
from .models import Device, Notification
from django.conf import settings
from django.utils import timezone

def send_push_notification(user, title, body, data=None):
    """
    Sends a push notification to all active devices of a given user.
    """
    if not firebase_admin._apps:
        print("Firebase app not initialized. Cannot send notification.")
        return

    registration_ids = list(Device.objects.filter(user=user, active=True).values_list('registration_id', flat=True))

    if not registration_ids:
        print(f"No active devices found for user {user.email}.")
        return
    
    # --- Create Notification record in the database ---
    try:
        notification_record = Notification.objects.create(
            user=user,
            title=title,
            body=body,
            data=data # This will store the custom data in the DB
        )
        # It's useful to include the notification_record.id in the FCM data payload
        # so the frontend knows which specific notification to mark as read.
        if data is None:
            data = {}
        data['notification_id'] = str(notification_record.id) # Convert UUID to string if using UUIDField for ID
        print(f"Created notification record {notification_record.id} for user {user.email}")
    except Exception as e:
        print(f"Error creating notification record for user {user.email}: {e}")
        # Decide if you want to abort push or continue without DB record
        return # Abort if DB record fails, as frontend needs this ID

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data,
        tokens=registration_ids,
    )

    try:
        response = messaging.send_each_for_multicast(message)
        print(f"Successfully sent {response.success_count} messages to user {user.email}.")
        if response.failure_count > 0:
            failed_tokens = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    print(f"Failed to send message: {resp.exception}")
                    failed_token = registration_ids[idx]
                    failed_tokens.append(failed_token)
                    if resp.exception and "NotRegistered" in str(resp.exception):
                        Device.objects.filter(registration_id=failed_token).update(active=False)
            print(f'List of tokens that caused failures: {failed_tokens}')
    except Exception as e:
        print(f"Error sending push notification to user {user.email}: {e}")
