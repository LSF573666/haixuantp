from rest_framework import serializers

from gifts.models import Gift, GiftTransaction


class GiftSerializer(serializers.ModelSerializer):
  class Meta:
    model = Gift
    fields = [
      'id', 'name', 'icon', 'price', 'heat_value',
      'description', 'is_active', 'sort_order',
    ]


class SendGiftSerializer(serializers.Serializer):
  """余额赠送礼物。"""

  candidate_id = serializers.IntegerField(help_text='候选人 ID')
  gift_id = serializers.IntegerField(help_text='礼物 ID')
  quantity = serializers.IntegerField(default=1, min_value=1, help_text='数量')


class PayGiftSerializer(serializers.Serializer):
  """按礼物价格直接发起第三方支付。金额 = 礼物单价 × 数量，无需用户传金额。"""

  candidate_id = serializers.IntegerField(help_text='候选人 ID')
  gift_id = serializers.IntegerField(help_text='礼物 ID')
  quantity = serializers.IntegerField(default=1, min_value=1, help_text='数量')
  payment_method = serializers.ChoiceField(
    choices=[('wechat', '微信支付'), ('alipay', '支付宝')],
    help_text='支付方式（金额由礼物价格自动计算）',
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


class GiftTransactionSerializer(serializers.ModelSerializer):
  gift_name = serializers.CharField(source='gift.name', read_only=True)
  candidate_name = serializers.CharField(source='candidate.name', read_only=True)

  class Meta:
    model = GiftTransaction
    fields = [
      'id', 'gift', 'gift_name', 'candidate', 'candidate_name',
      'quantity', 'total_price', 'total_heat', 'created_at',
    ]
