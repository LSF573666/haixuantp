from django.conf import settings
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import PayeeAccount, PaymentOrder, WithdrawOrder
from payments.serializers import (
  BindPayeeSerializer,
  CreateRechargeSerializer,
  CreateWithdrawSerializer,
  DevPaySerializer,
  PayeeAccountSerializer,
  PaymentOrderSerializer,
  UnbindPayeeSerializer,
  WithdrawOrderSerializer,
)
from payments.services import (
  bind_payee_account,
  complete_order,
  create_recharge_order,
  create_withdraw_order,
  handle_payment_notify,
  handle_withdraw_notify,
  unbind_payee_account,
)


class WalletBalanceView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(tags=['钱包'], summary='查询钱包余额')
  def get(self, request):
    request.user.refresh_from_db(fields=['balance'])
    return Response({'balance': str(request.user.balance)})


class CreateRechargeView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['钱包'],
    summary='创建充值订单',
    description='创建充值订单并返回微信/支付宝 Native 扫码支付参数（code_url / qr_code）。',
    request=CreateRechargeSerializer,
    responses={201: dict},
  )
  def post(self, request):
    serializer = CreateRechargeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data['amount']
    payment_method = serializer.validated_data['payment_method']

    try:
      order, pay_data = create_recharge_order(request.user, amount, payment_method)
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
      'order': PaymentOrderSerializer(order).data,
      'pay_data': pay_data,
    }, status=status.HTTP_201_CREATED)


class DevPayView(APIView):
  """开发环境模拟支付成功。"""

  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['钱包'],
    summary='模拟支付成功（仅开发环境）',
    request=DevPaySerializer,
    responses={200: PaymentOrderSerializer},
  )
  def post(self, request):
    if not settings.DEBUG:
      return Response({'detail': '仅开发环境可用'}, status=status.HTTP_403_FORBIDDEN)

    serializer = DevPaySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    order_no = serializer.validated_data['order_no']

    try:
      order = PaymentOrder.objects.get(
        order_no=order_no,
        user=request.user,
        status=PaymentOrder.Status.PENDING,
      )
    except PaymentOrder.DoesNotExist:
      return Response({'detail': '订单不存在'}, status=status.HTTP_404_NOT_FOUND)

    order = complete_order(order, transaction_id=f'DEV_{order_no}', raw_data={'dev': True})
    request.user.refresh_from_db(fields=['balance'])
    return Response({
      'message': '模拟支付成功',
      'order': PaymentOrderSerializer(order).data,
      'balance': str(request.user.balance),
    })


class OrderListView(generics.ListAPIView):
  permission_classes = [IsAuthenticated]
  serializer_class = PaymentOrderSerializer

  @extend_schema(tags=['钱包'], summary='我的支付订单列表')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def get_queryset(self):
    return self.request.user.orders.all()


class OrderDetailView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(tags=['钱包'], summary='查询支付订单状态')
  def get(self, request, order_no):
    try:
      order = PaymentOrder.objects.get(order_no=order_no, user=request.user)
    except PaymentOrder.DoesNotExist:
      return Response({'detail': '订单不存在'}, status=status.HTTP_404_NOT_FOUND)
    request.user.refresh_from_db(fields=['balance'])
    return Response({
      'order': PaymentOrderSerializer(order).data,
      'balance': str(request.user.balance),
    })


class PayeeAccountListView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(tags=['钱包'], summary='收款账户列表')
  def get(self, request):
    rows = PayeeAccount.objects.filter(user=request.user)
    return Response({'accounts': PayeeAccountSerializer(rows, many=True).data})

  @extend_schema(
    tags=['钱包'],
    summary='绑定收款账户',
    request=BindPayeeSerializer,
    responses={200: dict},
  )
  def post(self, request):
    serializer = BindPayeeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
      row = bind_payee_account(
        request.user,
        channel=serializer.validated_data['channel'],
        account=serializer.validated_data['account'],
        account_name=serializer.validated_data['account_name'],
      )
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({
      'message': '绑定成功',
      'account': PayeeAccountSerializer(row).data,
    })

  @extend_schema(
    tags=['钱包'],
    summary='解绑收款账户',
    request=UnbindPayeeSerializer,
  )
  def delete(self, request):
    serializer = UnbindPayeeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ok = unbind_payee_account(request.user, channel=serializer.validated_data['channel'])
    if not ok:
      return Response({'detail': '未绑定该渠道收款账户'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'message': '已解绑'})


class CreateWithdrawView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['钱包'],
    summary='申请提现',
    description=(
      '从余额提现到已绑定的微信 openid / 支付宝账号。'
      '微信新版商家转账可能返回 needUserConfirm，需前端拉起用户确认收款。'
    ),
    request=CreateWithdrawSerializer,
    responses={201: dict},
  )
  def post(self, request):
    serializer = CreateWithdrawSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
      order, confirm = create_withdraw_order(
        request.user,
        amount=serializer.validated_data['amount'],
        channel=serializer.validated_data['channel'],
      )
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    request.user.refresh_from_db(fields=['balance'])
    data = {
      'message': '提现已受理',
      'order': WithdrawOrderSerializer(order).data,
      'balance': str(request.user.balance),
    }
    if confirm:
      data['wechat_confirm'] = confirm
      data['message'] = '提现待用户在微信侧确认收款'
    return Response(data, status=status.HTTP_201_CREATED)


class WithdrawListView(generics.ListAPIView):
  permission_classes = [IsAuthenticated]
  serializer_class = WithdrawOrderSerializer

  @extend_schema(tags=['钱包'], summary='我的提现记录')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def get_queryset(self):
    return self.request.user.withdraw_orders.all()


def _notify_response(body):
  if isinstance(body, str):
    return HttpResponse(body, content_type='text/plain; charset=utf-8')
  return Response(body)


class WeChatNotifyView(APIView):
  permission_classes = [AllowAny]
  authentication_classes = []

  @extend_schema(tags=['钱包'], summary='微信支付回调', exclude=True)
  def post(self, request):
    ok, body, _ = handle_payment_notify(channel='wechat', request=request)
    resp = _notify_response(body)
    if not ok and isinstance(body, dict):
      return Response(body, status=status.HTTP_400_BAD_REQUEST)
    return resp


class AlipayNotifyView(APIView):
  permission_classes = [AllowAny]
  authentication_classes = []

  @extend_schema(tags=['钱包'], summary='支付宝支付回调', exclude=True)
  def post(self, request):
    post_data = {k: request.POST.get(k) for k in request.POST.keys()}
    if not post_data and isinstance(request.data, dict):
      post_data = dict(request.data)
    ok, body, _ = handle_payment_notify(channel='alipay', post_data=post_data)
    if not ok:
      return HttpResponse('fail', content_type='text/plain; charset=utf-8')
    return HttpResponse(body, content_type='text/plain; charset=utf-8')


class WeChatWithdrawNotifyView(APIView):
  permission_classes = [AllowAny]
  authentication_classes = []

  @extend_schema(tags=['钱包'], summary='微信提现回调', exclude=True)
  def post(self, request):
    ok, body, _ = handle_withdraw_notify(channel='wechat', request=request)
    if not ok and isinstance(body, dict):
      return Response(body, status=status.HTTP_400_BAD_REQUEST)
    return _notify_response(body)


class AlipayWithdrawNotifyView(APIView):
  permission_classes = [AllowAny]
  authentication_classes = []

  @extend_schema(tags=['钱包'], summary='支付宝提现回调', exclude=True)
  def post(self, request):
    post_data = {k: request.POST.get(k) for k in request.POST.keys()}
    if not post_data and isinstance(request.data, dict):
      post_data = dict(request.data)
    ok, body, _ = handle_withdraw_notify(channel='alipay', post_data=post_data)
    if not ok:
      return HttpResponse('fail', content_type='text/plain; charset=utf-8')
    return HttpResponse(body, content_type='text/plain; charset=utf-8')
