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


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE, OSS_STS_ROLE_ARN='')
class OSSStsCredentialTests(APITestCase):
  def setUp(self):
    self.user = User.objects.create_user(username='13800138001', phone='13800138001')
    self.url = reverse('oss-sts')

  def test_requires_authentication(self):
    response = self.client.get(self.url)
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

  def test_returns_503_when_sts_not_configured(self):
    self.client.force_authenticate(user=self.user)
    response = self.client.get(self.url)
    self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
    self.assertEqual(response.data['detail'], '未配置 OSS_STS_ROLE_ARN')
