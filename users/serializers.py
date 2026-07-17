import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from users.models import User


PHONE_REGEX = re.compile(r'^1[3-9]\d{9}$')


class SendSMSCodeSerializer(serializers.Serializer):
  phone = serializers.CharField(max_length=11, help_text='手机号')

  def validate_phone(self, value):
    if not PHONE_REGEX.match(value):
      raise serializers.ValidationError('手机号格式不正确')
    return value


class PhoneLoginSerializer(serializers.Serializer):
  phone = serializers.CharField(max_length=11, help_text='手机号')
  code = serializers.CharField(max_length=6, help_text='短信验证码')

  def validate_phone(self, value):
    if not PHONE_REGEX.match(value):
      raise serializers.ValidationError('手机号格式不正确')
    return value


class UserRegisterSerializer(serializers.Serializer):
  phone = serializers.CharField(max_length=11, help_text='手机号')
  code = serializers.CharField(max_length=6, help_text='短信验证码')
  password = serializers.CharField(
    max_length=128,
    write_only=True,
    required=False,
    help_text='登录密码（可选，注册时可直接设置）',
  )
  nickname = serializers.CharField(max_length=50, required=False, default='', help_text='昵称')

  def validate_phone(self, value):
    if not PHONE_REGEX.match(value):
      raise serializers.ValidationError('手机号格式不正确')
    if User.objects.filter(phone=value).exists():
      raise serializers.ValidationError('该手机号已注册')
    return value

  def validate_password(self, value):
    try:
      validate_password(value)
    except DjangoValidationError as e:
      raise serializers.ValidationError(list(e.messages))
    return value


class PasswordLoginSerializer(serializers.Serializer):
  phone = serializers.CharField(max_length=11, help_text='手机号')
  password = serializers.CharField(max_length=128, write_only=True, help_text='登录密码')

  def validate_phone(self, value):
    if not PHONE_REGEX.match(value):
      raise serializers.ValidationError('手机号格式不正确')
    return value


class SetPasswordSerializer(serializers.Serializer):
  code = serializers.CharField(max_length=6, help_text='短信验证码')
  password = serializers.CharField(max_length=128, write_only=True, help_text='新密码')

  def validate_password(self, value):
    user = self.context['request'].user
    try:
      validate_password(value, user)
    except DjangoValidationError as e:
      raise serializers.ValidationError(list(e.messages))
    return value


class UserSerializer(serializers.ModelSerializer):
  has_password = serializers.SerializerMethodField()

  class Meta:
    model = User
    fields = [
      'id', 'phone', 'nickname', 'avatar', 'balance', 'has_password',
      'created_at',
    ]
    read_only_fields = fields

  def get_has_password(self, obj) -> bool:
    return obj.has_usable_password()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['nickname', 'avatar']
