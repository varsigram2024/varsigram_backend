from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from smtplib import SMTPException
import logging

# Set up logging for the task
logger = logging.getLogger(__name__)

@shared_task(
    bind=True,  # Allows access to self (task instance)
    max_retries=3, # Maximum number of times to retry
    default_retry_delay=60 # Delay 60 seconds before first retry
)
def send_otp_email(self, email: str, otp: str):
    """
    Sends OTP email asynchronously with error handling and HTML content.
    """
    subject = "Varsigram: Your One-Time Password Code"
    from_email = settings.DEFAULT_FROM_EMAIL
    
    # Simple HTML content for better display
    html_message = f"""
    <html>
        <body>
            <p>Dear Varsigram User,</p>
            <p>Your OTP is: <strong>{otp}</strong></p>
            <p>This code is valid for 10 minutes. Please do not share it with anyone.</p>
            <br>
            <p>If you did not request this, please ignore this email.</p>
            <p>The Varsigram Team</p>
        </body>
    </html>
    """
    
    try:
        # Use send_mail with html_message for simplicity
        send_mail(
            subject=subject, 
            message=f"Your OTP is {otp}. It will expire in 10 minutes.", # Plain text fallback
            from_email=from_email, 
            recipient_list=[email],
            html_message=html_message, # Rich HTML content
            fail_silently=False # Ensure exceptions are raised
        )
        logger.info(f"OTP email successfully sent to {email}")
        return f"OTP email successfully sent to {email}"
        
    except SMTPException as exc:
        # Log the error and retry the task
        logger.error(f"SMTP Error sending OTP to {email}: {exc}")
        raise self.retry(exc=exc, countdown=60) # Retry with exponential backoff if needed
        
    except Exception as exc:
        # Catch all other exceptions (e.g., configuration issues)
        logger.critical(f"Unhandled Error sending OTP to {email}: {exc}")
        # Final failure - no more retries
        raise

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def send_reset_email(self, email: str, reset_link: str):
    """ Sends Reset Link email asynchronously with error handling and HTML content."""
    subject = "Varsigram: Password Reset Request"
    from_email = settings.DEFAULT_FROM_EMAIL
    
    html_message = f"""
    <html>
        <body>
            <p>Hi Varsigram User,</p>
            <p>We received a request to reset the password for your account.</p>
            <p>Click the link below to securely reset your password:</p>
            <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; color: white; background-color: #750015; text-decoration: none; border-radius: 5px;">
                Reset Password
            </a>
            <p>If you did not request a password reset, please ignore this email. Your current password will remain unchanged.</p>
            <br>
            <p>The Varsigram Team</p>
        </body>
    </html>
    """

    try:
        send_mail(
            subject=subject,
            message=f"Hi User,\n\nClick the link below to reset your password\n{reset_link}",
            from_email=from_email,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False
        )
        logger.info(f"Reset Link email successfully sent to {email}")
        return f"Reset Link email successfully sent to {email}"

    except SMTPException as exc:
        logger.error(f"SMTP Error sending reset link to {email}: {exc}")
        raise self.retry(exc=exc, countdown=60)

    except Exception as exc:
        logger.critical(f"Unhandled Error sending reset link to {email}: {exc}")
        raise
