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


class GiftTransactionSerializer(serializers.ModelSerializer):
  gift_name = serializers.CharField(source='gift.name', read_only=True)
  candidate_name = serializers.CharField(source='candidate.name', read_only=True)

  class Meta:
    model = GiftTransaction
    fields = [
      'id', 'gift', 'gift_name', 'candidate', 'candidate_name',
      'quantity', 'total_price', 'total_heat', 'created_at',
    ]
