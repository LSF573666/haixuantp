from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import PaymentOrder
from payments.serializers import CreateRechargeSerializer, DevPaySerializer, PaymentOrderSerializer
from payments.services import (
  AlipayService,
  WeChatPayService,
  complete_order,
  create_recharge_order,
)


class CreateRechargeView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['支付'],
    summary='创建充值订单',
    description='创建充值订单并返回支付参数（微信/支付宝）。',
    request=CreateRechargeSerializer,
    responses={201: dict},
  )
  def post(self, request):
    serializer = CreateRechargeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data['amount']
    payment_method = serializer.validated_data['payment_method']

    try:
      order = create_recharge_order(request.user, amount, payment_method)
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if payment_method == 'wechat':
      pay_data = WeChatPayService.create_order(order)
    else:
      pay_data = AlipayService.create_order(order)

    return Response({
      'order': PaymentOrderSerializer(order).data,
      'pay_data': pay_data,
    }, status=status.HTTP_201_CREATED)


class DevPayView(APIView):
  """开发环境模拟支付成功。"""

  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['支付'],
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

  @extend_schema(tags=['支付'], summary='我的订单列表')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def get_queryset(self):
    return self.request.user.orders.all()


class WeChatNotifyView(APIView):
  permission_classes = [AllowAny]
  authentication_classes = []

  @extend_schema(tags=['支付'], summary='微信支付回调', exclude=True)
  def post(self, request):
    # 实际生产环境解析 XML 并验证签名
    order_no = request.data.get('out_trade_no') or request.POST.get('out_trade_no')
    transaction_id = request.data.get('transaction_id', '')
    if not order_no:
      return Response({'code': 'FAIL', 'message': '缺少订单号'})

    try:
      order = PaymentOrder.objects.get(order_no=order_no, status=PaymentOrder.Status.PENDING)
      complete_order(order, transaction_id=transaction_id, raw_data=dict(request.data))
    except PaymentOrder.DoesNotExist:
      pass
    return Response({'code': 'SUCCESS', 'message': 'OK'})


class AlipayNotifyView(APIView):
  permission_classes = [AllowAny]
  authentication_classes = []

  @extend_schema(tags=['支付'], summary='支付宝支付回调', exclude=True)
  def post(self, request):
    order_no = request.data.get('out_trade_no') or request.POST.get('out_trade_no')
    transaction_id = request.data.get('trade_no', '')
    if not order_no:
      return Response('fail')

    try:
      order = PaymentOrder.objects.get(order_no=order_no, status=PaymentOrder.Status.PENDING)
      complete_order(order, transaction_id=transaction_id, raw_data=dict(request.data))
    except PaymentOrder.DoesNotExist:
      pass
    return Response('success')
