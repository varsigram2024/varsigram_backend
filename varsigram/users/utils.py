from rest_framework_jwt.settings import api_settings
from django.http import QueryDict
# ErrorHandlers

class ApplicationError(Exception):
    def __init__(self, message, extra=None):
        super().__init__(message)

        self.message = message
        self.extra = extra or {}



#Validators

def generate_jwt_token(user):
    """ Generate a JWT token for a user """
    jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
    payload = jwt_payload_handler(user)
    return jwt_encode_handler(payload)

def clean_data(data):
    """ Processes nested student/organization data from a dictionary """
    # Assuming 'data' is always a dict (JSON payload)

    # Ensure student/organization keys exist and are dicts, or set to None
    student_data = data.get('student')
    if not isinstance(student_data, dict) or not student_data.get('name'):
        data['student'] = None

    organization_data = data.get('organization')
    if not isinstance(organization_data, dict) or not organization_data.get('organization_name'):
        data['organization'] = None

    return data