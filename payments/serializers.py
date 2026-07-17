from decimal import Decimal

from rest_framework import serializers

from payments.models import PayeeAccount, PaymentOrder, WithdrawOrder


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
      'status', 'extra_data', 'paid_at', 'created_at',
    ]
    read_only_fields = fields


class DevPaySerializer(serializers.Serializer):
  order_no = serializers.CharField(help_text='订单号')


class WalletSerializer(serializers.Serializer):
  balance = serializers.DecimalField(max_digits=10, decimal_places=2)


class BindPayeeSerializer(serializers.Serializer):
  channel = serializers.ChoiceField(
    choices=[('wechat', '微信'), ('alipay', '支付宝')],
    help_text='wechat=微信openid；alipay=支付宝登录号（手机/邮箱）',
  )
  account = serializers.CharField(max_length=128, help_text='收款账号')
  account_name = serializers.CharField(max_length=64, help_text='收款人真实姓名')


class UnbindPayeeSerializer(serializers.Serializer):
  channel = serializers.ChoiceField(choices=[('wechat', '微信'), ('alipay', '支付宝')])


class PayeeAccountSerializer(serializers.ModelSerializer):
  account = serializers.SerializerMethodField()

  class Meta:
    model = PayeeAccount
    fields = ['channel', 'account', 'account_name', 'updated_at']
    read_only_fields = fields

  def get_account(self, obj):
    from payments.services import _mask_account
    return _mask_account(obj.account)


class CreateWithdrawSerializer(serializers.Serializer):
  amount = serializers.DecimalField(
    max_digits=10, decimal_places=2, min_value=Decimal('0.01'),
    help_text='提现金额（元）',
  )
  channel = serializers.ChoiceField(
    choices=[('wechat', '微信'), ('alipay', '支付宝')],
    help_text='提现渠道（须已绑定收款账户）',
  )


class WithdrawOrderSerializer(serializers.ModelSerializer):
  payee_account = serializers.SerializerMethodField()

  class Meta:
    model = WithdrawOrder
    fields = [
      'order_no', 'channel', 'amount', 'status',
      'payee_account', 'payee_name', 'provider_trade_no',
      'remark', 'completed_at', 'created_at',
    ]
    read_only_fields = fields

  def get_payee_account(self, obj):
    from payments.services import _mask_account
    return _mask_account(obj.payee_account)
