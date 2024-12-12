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

@shared_task
def send_reset_email(email, reset_link):
    """ Sends Reset Link email asynchronously."""
    subject = "Password Reset"
    message = f"Hi User,\n\nClick the link below to reset your password\n{reset_link}"
    from_email = "noreply@varsigram.org"
    recipient_list = [email]

    send_mail(subject=subject, message=message, from_email=from_email, recipient_list=recipient_list)
    return f"Reset Link sent to {email}"
