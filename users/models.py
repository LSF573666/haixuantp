from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
  """自定义用户模型。后台用 username 登录，前端 API 用手机号登录。"""

  phone = models.CharField('手机号', max_length=11, unique=True, null=True, blank=True, db_index=True)
  nickname = models.CharField('昵称', max_length=50, blank=True, default='')
  avatar = models.ImageField('头像', upload_to='avatars/', blank=True, null=True)
  balance = models.DecimalField('账户余额', max_digits=10, decimal_places=2, default=0)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)
  updated_at = models.DateTimeField('更新时间', auto_now=True)

  USERNAME_FIELD = 'username'
  REQUIRED_FIELDS = []

  class Meta:
    verbose_name = '用户'
    verbose_name_plural = '用户'
    ordering = ['-created_at']

  def __str__(self):
    return self.phone or self.username


class SMSCode(models.Model):
  """短信验证码记录。"""

  phone = models.CharField('手机号', max_length=11, db_index=True)
  code = models.CharField('验证码', max_length=6)
  is_used = models.BooleanField('已使用', default=False)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)
  expires_at = models.DateTimeField('过期时间')

  class Meta:
    verbose_name = '短信验证码'
    verbose_name_plural = '短信验证码'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.phone} - {self.code}'
