import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_verification_sms(phone: str, code: str) -> None:
  """通过阿里云短信服务发送验证码。"""
  from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
  from alibabacloud_dysmsapi20170525.client import Client
  from alibabacloud_tea_openapi import models as open_api_models

  config = open_api_models.Config(
    access_key_id=settings.ALIYUN_SMS_ACCESS_KEY_ID,
    access_key_secret=settings.ALIYUN_SMS_ACCESS_KEY_SECRET,
    region_id=settings.ALIYUN_SMS_REGION,
  )
  config.endpoint = 'dysmsapi.aliyuncs.com'
  client = Client(config)

  request = dysmsapi_models.SendSmsRequest(
    phone_numbers=phone,
    sign_name=settings.ALIYUN_SMS_SIGN_NAME,
    template_code=settings.ALIYUN_SMS_TEMPLATE_CODE,
    template_param=json.dumps({'code': code}, ensure_ascii=False),
  )
  response = client.send_sms(request)

  if response.body.code != 'OK':
    logger.error(
      'Aliyun SMS failed: code=%s message=%s request_id=%s',
      response.body.code,
      response.body.message,
      response.body.request_id,
    )
    if response.body.code == 'isv.BUSINESS_LIMIT_CONTROL':
      raise ValueError('发送过于频繁，请稍后再试')
    raise RuntimeError(f'短信发送失败: {response.body.message}')
