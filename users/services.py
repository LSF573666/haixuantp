import logging
import random
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.aliyun_sms import send_verification_sms
from users.models import SMSCode

logger = logging.getLogger(__name__)

# 与阿里云验证码「分钟级流控 Permits:1」对齐，避免无意义打到上游
SMS_SEND_COOLDOWN_SECONDS = 60


def send_sms_code(phone: str) -> str:
  """发送短信验证码。开发模式下返回固定验证码。"""
  latest = SMSCode.objects.filter(phone=phone).order_by('-created_at').first()
  if latest:
    elapsed = (timezone.now() - latest.created_at).total_seconds()
    if elapsed < SMS_SEND_COOLDOWN_SECONDS:
      wait = int(SMS_SEND_COOLDOWN_SECONDS - elapsed) or 1
      raise ValueError(f'发送过于频繁，请 {wait} 秒后再试')

  if settings.SMS_DEV_MODE:
    code = settings.SMS_DEV_CODE
  else:
    code = ''.join(str(random.randint(0, 9)) for _ in range(6))
    send_verification_sms(phone, code)

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
