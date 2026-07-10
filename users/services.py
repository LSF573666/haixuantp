import random
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from users.models import SMSCode


def send_sms_code(phone: str) -> str:
  """发送短信验证码。开发模式下返回固定验证码。"""
  if settings.SMS_DEV_MODE:
    code = settings.SMS_DEV_CODE
  else:
    code = ''.join(str(random.randint(0, 9)) for _ in range(6))
    # TODO: 接入真实短信服务商 API

  SMSCode.objects.create(
    phone=phone,
    code=code,
    expires_at=timezone.now() + timedelta(minutes=5),
  )
  return code


def verify_sms_code(phone: str, code: str) -> bool:
  """验证短信验证码。"""
  sms = (
    SMSCode.objects.filter(
      phone=phone,
      code=code,
      is_used=False,
      expires_at__gt=timezone.now(),
    )
    .order_by('-created_at')
    .first()
  )
  if not sms:
    return False
  sms.is_used = True
  sms.save(update_fields=['is_used'])
  return True
