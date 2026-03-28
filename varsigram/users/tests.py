from django.test import TestCase
from django.contrib.auth import get_user_model

from notifications_app.models import Device, Notification
from users.models import Student

User = get_user_model()


class UserHardDeleteTest(TestCase):
    def test_hard_delete_removes_user_and_related(self):
        user = User.objects.create_user(email='del@example.com', password='pass')

        # Attach a Student profile
        student = Student.objects.create(
            user=user,
            name='Test Student',
            faculty='FAC',
            department='DEPT',
            university='UNI',
            year='1',
            phone_number='123456',
            religion='None',
            sex='Other'
        )

        # Attach a Device and Notification
        Device.objects.create(user=user, registration_id='devtoken-1')
        Notification.objects.create(user=user, title='Hi', body='Body')

        # Sanity checks
        self.assertTrue(User.objects.all_with_deleted().filter(pk=user.pk).exists())
        self.assertTrue(Student.objects.filter(pk=student.pk).exists())
        self.assertTrue(Device.objects.filter(user=user).exists())
        self.assertTrue(Notification.objects.filter(user=user).exists())

        # Perform hard delete
        user.hard_delete()

        # Ensure everything is removed
        self.assertFalse(User.objects.all_with_deleted().filter(pk=user.pk).exists())
        self.assertFalse(Student.objects.filter(pk=student.pk).exists())
        self.assertFalse(Device.objects.filter(user=user).exists())
        self.assertFalse(Notification.objects.filter(user=user).exists())


class AdminHardDeleteViewTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='admin@example.com', password='adminpass')
        self.target = User.objects.create_user(email='target@example.com', password='targetpass')
        # add related objects
        self.student = Student.objects.create(
            user=self.target,
            name='Target', faculty='F', department='D', university='U', year='1', phone_number='1', religion='None', sex='Other'
        )
        Device.objects.create(user=self.target, registration_id='dev-1')
        Notification.objects.create(user=self.target, title='T', body='B')

    def test_admin_can_hard_delete_user(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.admin)

        resp = client.post(f'/api/v1/users/{self.target.pk}/hard-delete/', {'confirm': True}, format='json')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(User.objects.all_with_deleted().filter(pk=self.target.pk).exists())
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
        self.assertFalse(Device.objects.filter(user=self.target).exists())
        self.assertFalse(Notification.objects.filter(user=self.target).exists())

    def test_non_admin_cannot_hard_delete(self):
        from rest_framework.test import APIClient
        client = APIClient()
        normal = User.objects.create_user(email='u@example.com', password='p')
        client.force_authenticate(user=normal)
        resp = client.post(f'/api/v1/users/{self.target.pk}/hard-delete/', {'confirm': True}, format='json')
        self.assertEqual(resp.status_code, 403)


class SelfHardDeleteViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='selfdel@example.com', password='mypassword')
        self.student = Student.objects.create(
            user=self.user,
            name='Self', faculty='F', department='D', university='U', year='1', phone_number='1', religion='None', sex='Other'
        )
        Device.objects.create(user=self.user, registration_id='dev-2')
        Notification.objects.create(user=self.user, title='Hi', body='Body')

    def test_self_delete_requires_password_and_deletes(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.post('/api/v1/profile/hard-delete/', {'confirm': True, 'password': 'mypassword'}, format='json')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(User.objects.all_with_deleted().filter(pk=self.user.pk).exists())
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
        self.assertFalse(Device.objects.filter(user=self.user).exists())
        self.assertFalse(Notification.objects.filter(user=self.user).exists())

    def test_self_delete_wrong_password_fails(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.post('/api/v1/profile/hard-delete/', {'confirm': True, 'password': 'wrong'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(User.objects.all_with_deleted().filter(pk=self.user.pk).exists())
