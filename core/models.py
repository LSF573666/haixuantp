from django.conf import settings
from django.db import models


class FrontendRequestLog(models.Model):
  """前端 API 请求日志。"""

  user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name='用户',
    related_name='request_logs',
  )
  method = models.CharField('请求方法', max_length=10)
  path = models.CharField('请求路径', max_length=500)
  query_string = models.TextField('查询参数', blank=True, default='')
  request_body = models.TextField('请求体', blank=True, default='')
  response_body = models.TextField('响应体', blank=True, default='')
  status_code = models.PositiveSmallIntegerField('状态码')
  duration_ms = models.PositiveIntegerField('耗时(ms)')
  ip_address = models.GenericIPAddressField('IP 地址', null=True, blank=True)
  user_agent = models.CharField('User-Agent', max_length=500, blank=True, default='')
  created_at = models.DateTimeField('请求时间', auto_now_add=True, db_index=True)

  class Meta:
    verbose_name = '前端请求日志'
    verbose_name_plural = '前端请求日志'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.method} {self.path} [{self.status_code}]'


class SiteConfig(models.Model):
  """系统配置，后台可修改。"""

  key = models.CharField('配置键', max_length=100, unique=True)
  value = models.TextField('配置值')
  description = models.CharField('说明', max_length=255, blank=True, default='')
  updated_at = models.DateTimeField('更新时间', auto_now=True)

  class Meta:
    verbose_name = '系统配置'
    verbose_name_plural = '系统配置'

  def __str__(self):
    return f'{self.key} = {self.value}'

  @classmethod
  def get_value(cls, key, default=None):
    try:
      return cls.objects.get(key=key).value
    except cls.DoesNotExist:
      return default

  @classmethod
  def get_int(cls, key, default=0):
    value = cls.get_value(key)
    if value is None:
      return default
    try:
      return int(value)
    except (TypeError, ValueError):
      return default

  @classmethod
  def set_value(cls, key, value, description=''):
    obj, _ = cls.objects.update_or_create(
      key=key,
      defaults={'value': str(value), 'description': description},
    )
    return obj
