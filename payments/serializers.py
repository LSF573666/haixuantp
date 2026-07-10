from decimal import Decimal

from rest_framework import serializers

from payments.models import PaymentOrder


class CreateRechargeSerializer(serializers.Serializer):
  amount = serializers.DecimalField(
    max_digits=10, decimal_places=2, min_value=Decimal('0.01'),
    help_text='充值金额（元）',
  )
  payment_method = serializers.ChoiceField(
    choices=[('wechat', '微信支付'), ('alipay', '支付宝')],
    help_text='支付方式',
  )


class PaymentOrderSerializer(serializers.ModelSerializer):
  class Meta:
    model = PaymentOrder
    fields = [
      'order_no', 'order_type', 'payment_method', 'amount',
      'status', 'paid_at', 'created_at',
    ]
    read_only_fields = fields


class DevPaySerializer(serializers.Serializer):
  order_no = serializers.CharField(help_text='订单号')
