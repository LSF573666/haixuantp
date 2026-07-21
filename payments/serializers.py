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
  payment_mode = serializers.ChoiceField(
    choices=[
      ('native', 'Native 扫码'),
      ('jsapi', 'JSAPI 微信内支付'),
      ('h5', '支付宝 H5 手机网站支付'),
    ],
    default='native',
    required=False,
    help_text='支付模式：native=扫码（默认）；jsapi=微信内调起（需 openid）；h5=支付宝手机网站跳转',
  )
  openid = serializers.CharField(
    required=False,
    allow_blank=True,
    max_length=128,
    help_text='微信用户 openid；payment_mode=jsapi 时必填，须与商户 AppID 对应',
  )

  def validate(self, attrs):
    payment_method = attrs.get('payment_method')
    payment_mode = (attrs.get('payment_mode') or 'native').strip().lower()
    openid = (attrs.get('openid') or '').strip()
    if payment_mode in ('wap',):
      payment_mode = 'h5'
    attrs['payment_mode'] = payment_mode
    attrs['openid'] = openid
    if payment_method == 'wechat' and payment_mode == 'jsapi' and not openid:
      raise serializers.ValidationError({'openid': 'JSAPI 支付需要传微信用户 openid'})
    if payment_method == 'wechat' and payment_mode == 'h5':
      raise serializers.ValidationError({'payment_mode': '微信暂不支持 h5，请使用 native 或 jsapi'})
    if payment_method == 'alipay' and payment_mode == 'jsapi':
      raise serializers.ValidationError({'payment_mode': '支付宝暂不支持 jsapi，请使用 native 或 h5'})
    return attrs


class CreateRechargeJsapiSerializer(serializers.Serializer):
  """专用 JSAPI 充值：强制微信 JSAPI，openid 可由请求传入。"""

  amount = serializers.DecimalField(
    max_digits=10, decimal_places=2, min_value=Decimal('0.01'),
    help_text='充值金额（元）',
  )
  openid = serializers.CharField(
    required=False,
    allow_blank=True,
    max_length=128,
    help_text='微信用户 openid（与商户 AppID 对应）；未传时尝试使用已绑定的微信收款账号',
  )
  payment_method = serializers.ChoiceField(
    choices=[('wechat', '微信支付')],
    default='wechat',
    required=False,
    help_text='固定为 wechat',
  )

  def validate(self, attrs):
    attrs['payment_method'] = 'wechat'
    attrs['openid'] = (attrs.get('openid') or '').strip()
    return attrs


class PaymentOrderSerializer(serializers.ModelSerializer):
  status_display = serializers.CharField(source='get_status_display', read_only=True)

  class Meta:
    model = PaymentOrder
    fields = [
      'order_no', 'order_type', 'payment_method', 'amount',
      'status', 'status_display', 'extra_data', 'paid_at', 'created_at',
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
