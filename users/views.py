from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import (
  PhoneLoginSerializer,
  SendSMSCodeSerializer,
  UserProfileUpdateSerializer,
  UserSerializer,
)
from users.services import send_sms_code, verify_sms_code

User = get_user_model()


class SendSMSCodeView(APIView):
  permission_classes = [AllowAny]

  @extend_schema(
    tags=['认证'],
    summary='发送短信验证码',
    request=SendSMSCodeSerializer,
    responses={200: dict},
  )
  def post(self, request):
    serializer = SendSMSCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = serializer.validated_data['phone']
    send_sms_code(phone)
    return Response({'message': '验证码已发送', 'phone': phone})


class PhoneLoginView(APIView):
  permission_classes = [AllowAny]

  @extend_schema(
    tags=['认证'],
    summary='手机号登录',
    description='使用手机号和短信验证码登录，返回 JWT access/refresh token。',
    request=PhoneLoginSerializer,
    responses={200: dict},
  )
  def post(self, request):
    serializer = PhoneLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = serializer.validated_data['phone']
    code = serializer.validated_data['code']

    if not verify_sms_code(phone, code):
      return Response({'detail': '验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(
      phone=phone,
      defaults={'username': phone},
    )
    refresh = RefreshToken.for_user(user)
    return Response({
      'access': str(refresh.access_token),
      'refresh': str(refresh),
      'user': UserSerializer(user).data,
      'is_new_user': created,
    })


class UserProfileView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(tags=['认证'], summary='获取当前用户信息', responses={200: UserSerializer})
  def get(self, request):
    return Response(UserSerializer(request.user).data)

  @extend_schema(
    tags=['认证'],
    summary='更新用户信息',
    request=UserProfileUpdateSerializer,
    responses={200: UserSerializer},
  )
  def patch(self, request):
    serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(UserSerializer(request.user).data)
