from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_otp_email(email, otp):
    """Send OTP email asynchronously."""
    subject = "Your OTP Code"
    message = f"Your OTP is {otp}. It will expire in 10 minutes."
    from_email = "noreply@varsigram.org"
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)
    return f"OTP email sent to {email}"
