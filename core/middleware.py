import json
import re
import time

from django.utils.deprecation import MiddlewareMixin

from core.models import FrontendRequestLog

SENSITIVE_KEYS = re.compile(
  r'(password|token|refresh|access|secret|code|authorization)',
  re.IGNORECASE,
)
MAX_BODY_LENGTH = 2000
API_PREFIXES = (
  '/api/auth/',
  '/api/candidates/',
  '/api/votes/',
  '/api/gifts/',
  '/api/payments/',
  '/api/config/',
  '/auth/',
  '/candidates/',
  '/votes/',
  '/gifts/',
  '/payments/',
  '/config/',
)
SKIP_PREFIXES = (
  '/admin/',
  '/static/',
  '/media/',
  '/api/schema/',
  '/api/docs/',
  '/api/redoc/',
)


def _get_client_ip(request):
  forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
  if forwarded:
    return forwarded.split(',')[0].strip()
  return request.META.get('REMOTE_ADDR')


def _mask_sensitive_data(data):
  if isinstance(data, dict):
    return {
      key: '***' if SENSITIVE_KEYS.search(str(key)) else _mask_sensitive_data(value)
      for key, value in data.items()
    }
  if isinstance(data, list):
    return [_mask_sensitive_data(item) for item in data]
  return data


class FrontendRequestLogMiddleware(MiddlewareMixin):
  def process_request(self, request):
    request._log_start_time = time.monotonic()
    request._should_log_request = self._should_log(request)
    request._request_content_type = request.META.get('CONTENT_TYPE', '')
    request._log_request_body_raw = b''
    if request._should_log_request and request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
      try:
        request._log_request_body_raw = request.body
      except Exception:
        request._log_request_body_raw = b''

  def process_response(self, request, response):
    if not getattr(request, '_should_log_request', False):
      return response

    duration_ms = int(
      (time.monotonic() - getattr(request, '_log_start_time', time.monotonic())) * 1000
    )
    user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    if user is None:
      user = self._get_user_from_jwt(request)

    request_body = ''
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
      request_body = self._extract_request_body(request)

    try:
      FrontendRequestLog.objects.create(
        user=user,
        method=request.method,
        path=request.path[:500],
        query_string=request.META.get('QUERY_STRING', '')[:2000],
        request_body=request_body,
        status_code=response.status_code,
        duration_ms=duration_ms,
        ip_address=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
      )
    except Exception:
      pass

    return response

  def _should_log(self, request):
    path = request.path
    if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
      return False
    return any(path.startswith(prefix) for prefix in API_PREFIXES)

  def _get_user_from_jwt(self, request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
      return None
    try:
      from rest_framework_simplejwt.authentication import JWTAuthentication

      result = JWTAuthentication().authenticate(request)
      if result:
        return result[0]
    except Exception:
      return None
    return None

  def _extract_request_body(self, request):
    content_type = getattr(request, '_request_content_type', request.META.get('CONTENT_TYPE', ''))
    raw_body = getattr(request, '_log_request_body_raw', b'')
    if not raw_body:
      return ''

    try:
      text = raw_body.decode('utf-8')
    except UnicodeDecodeError:
      return '[binary data]'

    if 'application/json' in content_type or text.strip().startswith(('{', '[')):
      try:
        payload = _mask_sensitive_data(json.loads(text))
        text = json.dumps(payload, ensure_ascii=False)
      except (TypeError, ValueError):
        pass

    if len(text) > MAX_BODY_LENGTH:
      return text[:MAX_BODY_LENGTH] + '...'
    return text
