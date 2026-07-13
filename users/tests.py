from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

TEST_MIDDLEWARE = [
  'django.middleware.security.SecurityMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.middleware.common.CommonMiddleware',
  'django.middleware.csrf.CsrfViewMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class PasswordAuthTests(APITestCase):
  def setUp(self):
    self.user = User.objects.create_user(username='13800138000', phone='13800138000')
    self.set_password_url = reverse('set-password')
    self.password_login_url = reverse('password-login')

  def test_set_password_first_time(self):
    self.client.force_authenticate(user=self.user)
    response = self.client.post(self.set_password_url, {'password': 'TestPass123'})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.user.refresh_from_db()
    self.assertTrue(self.user.has_usable_password())
    self.assertTrue(self.user.check_password('TestPass123'))

  def test_change_password_requires_old_password(self):
    self.user.set_password('OldPass123')
    self.user.save()
    self.client.force_authenticate(user=self.user)

    response = self.client.post(self.set_password_url, {'password': 'NewPass123'})
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    response = self.client.post(
      self.set_password_url,
      {'old_password': 'OldPass123', 'password': 'NewPass123'},
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.user.refresh_from_db()
    self.assertTrue(self.user.check_password('NewPass123'))

  def test_password_login_success(self):
    self.user.set_password('TestPass123')
    self.user.save()
    response = self.client.post(
      self.password_login_url,
      {'phone': '13800138000', 'password': 'TestPass123'},
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertIn('access', response.data)
    self.assertIn('refresh', response.data)
    self.assertTrue(response.data['user']['has_password'])

  def test_password_login_wrong_password(self):
    self.user.set_password('TestPass123')
    self.user.save()
    response = self.client.post(
      self.password_login_url,
      {'phone': '13800138000', 'password': 'WrongPass123'},
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response.data['detail'], '手机号或密码错误')

  def test_password_login_without_password_set(self):
    response = self.client.post(
      self.password_login_url,
      {'phone': '13800138000', 'password': 'TestPass123'},
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response.data['detail'], '手机号或密码错误')
