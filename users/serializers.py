import re

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


class UserSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['id', 'phone', 'nickname', 'avatar', 'balance', 'created_at']
    read_only_fields = fields


class UserProfileUpdateSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['nickname', 'avatar']
