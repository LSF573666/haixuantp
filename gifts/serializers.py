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
  candidate_id = serializers.IntegerField(help_text='候选人 ID')
  gift_id = serializers.IntegerField(help_text='礼物 ID')
  quantity = serializers.IntegerField(default=1, min_value=1, help_text='数量')


class GiftTransactionSerializer(serializers.ModelSerializer):
  gift_name = serializers.CharField(source='gift.name', read_only=True)
  candidate_name = serializers.CharField(source='candidate.name', read_only=True)

  class Meta:
    model = GiftTransaction
    fields = [
      'id', 'gift', 'gift_name', 'candidate', 'candidate_name',
      'quantity', 'total_price', 'total_heat', 'created_at',
    ]
