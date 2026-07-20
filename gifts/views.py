from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gifts.models import Gift
from gifts.serializers import (
  GiftSerializer,
  GiftTransactionSerializer,
  PayGiftSerializer,
  SendGiftSerializer,
)
from gifts.services import send_gift
from payments.serializers import PaymentOrderSerializer
from payments.services import create_gift_payment_order


class GiftListView(generics.ListAPIView):
  permission_classes = [AllowAny]
  serializer_class = GiftSerializer
  queryset = Gift.objects.filter(is_active=True)

  @extend_schema(tags=['礼物'], summary='获取礼物列表')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)


class SendGiftView(APIView):
  """使用账户余额立即赠送礼物。"""

  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['礼物'],
    summary='余额赠送礼物',
    description='按礼物单价 × 数量扣减余额并立即赠送。第三方支付请用 POST /api/gifts/pay/。',
    request=SendGiftSerializer,
    responses={201: dict},
  )
  def post(self, request):
    serializer = SendGiftSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
      record = send_gift(
        request.user,
        serializer.validated_data['candidate_id'],
        serializer.validated_data['gift_id'],
        serializer.validated_data.get('quantity', 1),
      )
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
      'message': '礼物赠送成功',
      'payment_method': 'balance',
      'transaction': GiftTransactionSerializer(record).data,
      'balance': str(request.user.balance),
    }, status=status.HTTP_201_CREATED)


class PayGiftView(APIView):
  """按礼物价格直接发起微信/支付宝支付，支付成功后自动赠送。"""

  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['礼物'],
    summary='按礼物价格发起支付',
    description=(
      '根据礼物单价 × 数量自动计算应付金额，创建微信/支付宝订单。\n'
      '- 微信 Native（默认）：用 `pay_data.code_url` / `qr_code` 展示二维码\n'
      '- 微信 JSAPI：传 `payment_mode=jsapi` 与 `openid`，用 `pay_data.jsapi_params` 调起支付\n'
      '- 支付宝 Native：扫码（`qr_code`）\n'
      '- 支付宝 H5：传 `payment_mode=h5`，用 `pay_data.pay_url` 跳转手机网站支付\n'
      '支付成功后服务端回调自动赠送，可用订单号轮询状态。'
    ),
    request=PayGiftSerializer,
    responses={201: dict},
  )
  def post(self, request):
    serializer = PayGiftSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    gift_id = serializer.validated_data['gift_id']
    quantity = serializer.validated_data.get('quantity', 1)
    payment_method = serializer.validated_data['payment_method']
    payment_mode = serializer.validated_data.get('payment_mode', 'native')
    openid = serializer.validated_data.get('openid', '')

    try:
      gift = Gift.objects.get(pk=gift_id, is_active=True)
    except Gift.DoesNotExist:
      return Response({'detail': '礼物不存在或已下架'}, status=status.HTTP_400_BAD_REQUEST)

    unit_price = gift.price
    try:
      order, pay_data = create_gift_payment_order(
        request.user,
        serializer.validated_data['candidate_id'],
        gift_id,
        quantity,
        payment_method,
        payment_mode=payment_mode,
        openid=openid,
      )
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
      'message': '请完成支付，支付成功后礼物将自动赠送',
      'gift': {
        'id': gift.id,
        'name': gift.name,
        'unit_price': str(unit_price),
        'heat_value': gift.heat_value,
        'quantity': quantity,
        'total_amount': str(order.amount),
        'total_heat': gift.heat_value * quantity,
      },
      'payment_method': payment_method,
      'order': PaymentOrderSerializer(order).data,
      'pay_data': pay_data,
    }, status=status.HTTP_201_CREATED)


class GiftHistoryView(generics.ListAPIView):
  permission_classes = [IsAuthenticated]
  serializer_class = GiftTransactionSerializer

  @extend_schema(tags=['礼物'], summary='我的礼物赠送记录')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def get_queryset(self):
    return self.request.user.sent_gifts.select_related('gift', 'candidate').all()
