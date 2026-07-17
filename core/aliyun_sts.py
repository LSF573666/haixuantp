import json
import logging
import time

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_region_id() -> str:
  region = getattr(settings, 'OSS_REGION', '') or settings.ALIYUN_SMS_REGION
  if region:
    return region
  endpoint = settings.OSS_ENDPOINT
  if endpoint.startswith('oss-') and '.aliyuncs.com' in endpoint:
    return endpoint.removeprefix('oss-').removesuffix('.aliyuncs.com')
  return 'cn-hangzhou'


def get_oss_upload_policy(upload_dir: str) -> str:
  """生成限制上传目录的 RAM 策略。"""
  bucket_name = settings.ALIYUN_OSS_BUCKET
  resource = f'acs:oss:*:*:{bucket_name}/{upload_dir}*'
  policy = {
    'Version': '1',
    'Statement': [
      {
        'Effect': 'Allow',
        'Action': [
          'oss:PutObject',
          'oss:GetObject',
          'oss:AbortMultipartUpload',
          'oss:ListParts',
          'oss:InitiateMultipartUpload',
          'oss:CompleteMultipartUpload',
        ],
        'Resource': [resource],
      }
    ],
  }
  return json.dumps(policy, ensure_ascii=False)


def _create_sts_client(region_id: str):
  try:
    from alibabacloud_sts20150401.client import Client
    from alibabacloud_tea_openapi import models as open_api_models
  except ImportError as exc:
    raise RuntimeError('缺少 alibabacloud_sts20150401，请执行 pip install -r requirements.txt') from exc

  config = open_api_models.Config(
    access_key_id=settings.OSS_ACCESS_KEY_ID,
    access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
    region_id=region_id,
  )
  config.endpoint = 'sts.aliyuncs.com'
  return Client(config)


def _request_sts_credentials(user_id: int, upload_dir: str, region_id: str) -> dict:
  from alibabacloud_sts20150401 import models as sts_models

  client = _create_sts_client(region_id)
  request = sts_models.AssumeRoleRequest(
    role_arn=settings.OSS_STS_ROLE_ARN,
    role_session_name=f'haixuan-user-{user_id}',
    duration_seconds=settings.OSS_STS_DURATION_SECONDS,
    policy=get_oss_upload_policy(upload_dir),
  )

  last_error = None
  for attempt in range(3):
    try:
      response = client.assume_role(request)
      body = response.body
      if not body or not body.credentials:
        raise RuntimeError('STS 响应缺少凭证信息')
      credentials = body.credentials
      return {
        'Credentials': {
          'AccessKeyId': credentials.access_key_id,
          'AccessKeySecret': credentials.access_key_secret,
          'SecurityToken': credentials.security_token,
          'Expiration': credentials.expiration,
        }
      }
    except RuntimeError:
      raise
    except Exception as exc:
      last_error = exc
      logger.warning(
        'Aliyun STS AssumeRole failed (attempt %s/3): %s',
        attempt + 1,
        exc,
      )
      if attempt < 2:
        time.sleep(0.5 * (attempt + 1))
        continue
      raise RuntimeError(f'STS 服务调用失败: {exc}') from exc

  raise RuntimeError(f'STS 服务调用失败: {last_error}')


def assume_oss_upload_role(user_id: int) -> dict:
  """为前端直传 OSS 申请 STS 临时凭证。"""
  if not settings.OSS_STS_ROLE_ARN:
    raise RuntimeError('未配置 OSS_STS_ROLE_ARN')
  if not settings.OSS_ACCESS_KEY_ID or not settings.OSS_ACCESS_KEY_SECRET:
    raise RuntimeError('未配置 OSS AccessKey')
  if not settings.ALIYUN_OSS_BUCKET:
    raise RuntimeError('未配置 OSS Bucket')

  region_id = _get_region_id()
  upload_dir = f'uploads/{user_id}/'
  payload = _request_sts_credentials(user_id, upload_dir, region_id)
  credentials = payload['Credentials']

  endpoint = settings.OSS_ENDPOINT
  bucket = settings.ALIYUN_OSS_BUCKET
  base_url = settings.OSS_BASE_URL or f'https://{bucket}.{endpoint}'

  return {
    'access_key_id': credentials['AccessKeyId'],
    'access_key_secret': credentials['AccessKeySecret'],
    'security_token': credentials['SecurityToken'],
    'expiration': credentials['Expiration'],
    'bucket': bucket,
    'endpoint': endpoint,
    'region': region_id,
    'upload_dir': upload_dir,
    'base_url': base_url.rstrip('/'),
  }
