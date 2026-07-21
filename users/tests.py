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


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE, SMS_DEV_MODE=True, SMS_DEV_CODE='123456')
class UserRegisterTests(APITestCase):
  def setUp(self):
    self.send_sms_url = reverse('send-sms')
    self.register_url = reverse('user-register')

  def test_register_success(self):
    self.client.post(self.send_sms_url, {'phone': '13900139000'})
    response = self.client.post(
      self.register_url,
      {'phone': '13900139000', 'code': '123456', 'nickname': '新用户', 'password': 'TestPass123'},
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertIn('access', response.data)
    self.assertTrue(response.data['is_new_user'])
    self.assertEqual(response.data['user']['phone'], '13900139000')
    self.assertEqual(response.data['user']['nickname'], '新用户')
    self.assertTrue(response.data['user']['has_password'])

  def test_register_duplicate_phone(self):
    User.objects.create_user(username='13900139001', phone='13900139001')
    self.client.post(self.send_sms_url, {'phone': '13900139001'})
    response = self.client.post(
      self.register_url,
      {'phone': '13900139001', 'code': '123456'},
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn('phone', response.data)

  def test_register_invalid_code(self):
    self.client.post(self.send_sms_url, {'phone': '13900139002'})
    response = self.client.post(
      self.register_url,
      {'phone': '13900139002', 'code': '000000'},
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response.data['detail'], '验证码错误或已过期')


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE, SMS_DEV_MODE=True, SMS_DEV_CODE='123456')
class PasswordAuthTests(APITestCase):
  def setUp(self):
    self.user = User.objects.create_user(username='13800138000', phone='13800138000')
    self.send_sms_url = reverse('send-sms')
    self.set_password_url = reverse('set-password')
    self.password_login_url = reverse('password-login')

  def _send_sms(self, phone='13800138000'):
    self.client.post(self.send_sms_url, {'phone': phone})

  def test_set_password_first_time(self):
    self._send_sms()
    self.client.force_authenticate(user=self.user)
    response = self.client.post(
      self.set_password_url,
      {'code': '123456', 'password': 'TestPass123'},
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.user.refresh_from_db()
    self.assertTrue(self.user.has_usable_password())
    self.assertTrue(self.user.check_password('TestPass123'))

  def test_change_password_requires_sms_code(self):
    self.user.set_password('OldPass123')
    self.user.save()
    self.client.force_authenticate(user=self.user)

    response = self.client.post(self.set_password_url, {'password': 'NewPass123'})
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    response = self.client.post(
      self.set_password_url,
      {'code': '000000', 'password': 'NewPass123'},
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response.data['detail'], '验证码错误或已过期')

    self._send_sms()
    response = self.client.post(
      self.set_password_url,
      {'code': '123456', 'password': 'NewPass123'},
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

  def test_password_login_unregistered_phone(self):
    response = self.client.post(
      self.password_login_url,
      {'phone': '13900139999', 'password': 'TestPass123'},
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response.data['detail'], '手机号尚未注册')


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE, SMS_DEV_MODE=True, SMS_DEV_CODE='123456')
class PhoneLoginTests(APITestCase):
  def setUp(self):
    self.send_sms_url = reverse('send-sms')
    self.login_url = reverse('phone-login')
    self.user = User.objects.create_user(username='13800138001', phone='13800138001')

  def test_phone_login_success(self):
    self.client.post(self.send_sms_url, {'phone': '13800138001'})
    response = self.client.post(
      self.login_url,
      {'phone': '13800138001', 'code': '123456'},
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertIn('access', response.data)
    self.assertFalse(response.data['is_new_user'])

  def test_phone_login_unregistered(self):
    self.client.post(self.send_sms_url, {'phone': '13900139998'})
    response = self.client.post(
      self.login_url,
      {'phone': '13900139998', 'code': '123456'},
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertEqual(response.data['detail'], '手机号尚未注册')
    self.assertFalse(User.objects.filter(phone='13900139998').exists())
