from django.core.exceptions import PermissionDenied
import os

def validate_microsoft_email_domain(backend, user, response, *args, **kwargs):
    institution_domain = os.environ.get('INSTITUTION_DOMAIN')

    # Get the user's email from the response object (from Microsoft)
    email = response.get('email', '').lower()

    # Validate the email domain
    if email and email.split('@')[1] != institution_domain:
        raise PermissionDenied("Your email is not from a valid institutional domain.")
    
    #stores the validated email address in the user object
    user.email = email
    user.save()

    return user