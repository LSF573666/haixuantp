from rest_framework import serializers

from core.models import SiteConfig


class SiteConfigSerializer(serializers.ModelSerializer):
  class Meta:
    model = SiteConfig
    fields = ['key', 'value', 'description', 'updated_at']


class PublicConfigSerializer(serializers.Serializer):
  daily_vote_limit = serializers.IntegerField(help_text='每日投票上限')


class OSSStsCredentialSerializer(serializers.Serializer):
  access_key_id = serializers.CharField(help_text='STS 临时 AccessKey ID')
  access_key_secret = serializers.CharField(help_text='STS 临时 AccessKey Secret')
  security_token = serializers.CharField(help_text='STS SecurityToken')
  expiration = serializers.CharField(help_text='凭证过期时间')
  bucket = serializers.CharField(help_text='OSS Bucket 名称')
  endpoint = serializers.CharField(help_text='OSS Endpoint')
  region = serializers.CharField(help_text='OSS 区域')
  upload_dir = serializers.CharField(help_text='允许上传的目录前缀')
  base_url = serializers.CharField(help_text='文件访问基础 URL')
