from rest_framework import serializers

from core.models import SiteConfig


class SiteConfigSerializer(serializers.ModelSerializer):
  class Meta:
    model = SiteConfig
    fields = ['key', 'value', 'description', 'updated_at']


class PublicConfigSerializer(serializers.Serializer):
  daily_vote_limit = serializers.IntegerField(help_text='每日投票上限')
