from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import (
  PasswordLoginSerializer,
  PhoneLoginSerializer,
  SendSMSCodeSerializer,
  SetPasswordSerializer,
  UserProfileUpdateSerializer,
  UserRegisterSerializer,
  UserSerializer,
)
from users.services import send_sms_code, verify_sms_code

User = get_user_model()


def _login_response(user, is_new_user=False):
  refresh = RefreshToken.for_user(user)
  return Response({
    'access': str(refresh.access_token),
    'refresh': str(refresh),
    'user': UserSerializer(user).data,
    'is_new_user': is_new_user,
  })


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


class UserRegisterView(APIView):
  permission_classes = [AllowAny]

  @extend_schema(
    tags=['认证'],
    summary='新用户注册',
    description='使用手机号和短信验证码注册新账号，可选设置昵称和登录密码。注册成功后自动登录并返回 JWT。',
    request=UserRegisterSerializer,
    responses={201: dict},
  )
  def post(self, request):
    serializer = UserRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = serializer.validated_data['phone']
    code = serializer.validated_data['code']
    password = serializer.validated_data.get('password')
    nickname = serializer.validated_data.get('nickname', '')

    if not verify_sms_code(phone, code):
      return Response({'detail': '验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=phone, phone=phone, nickname=nickname)
    if password:
      user.set_password(password)
      user.save(update_fields=['password'])

    response = _login_response(user, is_new_user=True)
    response.status_code = status.HTTP_201_CREATED
    return response


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
    return _login_response(user, is_new_user=created)


class PasswordLoginView(APIView):
  permission_classes = [AllowAny]

  @extend_schema(
    tags=['认证'],
    summary='密码登录',
    description='使用手机号和密码登录，需已设置登录密码。返回 JWT access/refresh token。',
    request=PasswordLoginSerializer,
    responses={200: dict},
  )
  def post(self, request):
    serializer = PasswordLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = serializer.validated_data['phone']
    password = serializer.validated_data['password']

    try:
      user = User.objects.get(phone=phone)
    except User.DoesNotExist:
      return Response({'detail': '手机号或密码错误'}, status=status.HTTP_400_BAD_REQUEST)

    if not user.has_usable_password() or not user.check_password(password):
      return Response({'detail': '手机号或密码错误'}, status=status.HTTP_400_BAD_REQUEST)

    return _login_response(user)


class SetPasswordView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['认证'],
    summary='设置/修改登录密码',
    description='需先向当前账号手机号发送验证码，验证通过后方可设置或修改密码。',
    request=SetPasswordSerializer,
    responses={200: dict},
  )
  def post(self, request):
    serializer = SetPasswordSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)

    if not verify_sms_code(request.user.phone, serializer.validated_data['code']):
      return Response({'detail': '验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)

    request.user.set_password(serializer.validated_data['password'])
    request.user.save(update_fields=['password'])
    return Response({'message': '密码设置成功'})


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
