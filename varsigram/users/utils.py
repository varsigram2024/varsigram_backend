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
    """ Converts QueryDict to a dictionary """

    if isinstance(data, QueryDict):
        # Convert QueryDict to a regular dictionary
        data = data.dict()

    student_data = {}
    organization_data = {}

    for key, value in data.items():
        if key.startswith('student.'):
            student_data[key.replace('student.', '')] = value
        elif key.startswith('organization.'):
            organization_data[key.replace('organization.', '')] = value
    
    if student_data and student_data.get('name'):
        data['student'] = student_data
    else:
        data['student'] = None
    
    if organization_data and organization_data.get('organization_name'):
        data['organization'] = organization_data
    else:
        data['organization'] = None

    return data