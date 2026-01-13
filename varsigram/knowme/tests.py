from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch, Mock
from .models import Wall
from django.core.files.uploadedfile import SimpleUploadedFile


class JoinWallPhotoUploadTest(TestCase):
    def setUp(self):
        self.wall = Wall.objects.create(name='Test Wall', description='desc', creator_email='owner@example.com')

    @patch('postMang.apps.get_firebase_storage_client')
    @patch('users.tasks.send_wall_notification_email.delay')
    def test_join_wall_upload_and_schedule_email(self, mock_send_delay, mock_get_client):
        bucket = Mock()
        bucket.name = 'fake-bucket'
        blob = Mock()
        bucket.blob.return_value = blob
        mock_get_client.return_value = bucket

        url = reverse('join-wall', kwargs={'wall_id': self.wall.id})

        small_gif = SimpleUploadedFile('test.jpg', b'filecontent', content_type='image/jpeg')
        data = {
            'full_name': 'John Doe',
            'contact_info': 'john@example.com',
            'interests': 'testing',
            'photo': small_gif,
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, 201)
        mock_get_client.assert_called()
        mock_send_delay.assert_called()