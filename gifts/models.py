from django.conf import settings
from django.db import models

from candidates.models import Candidate


class Gift(models.Model):
  """礼物定义。"""

  name = models.CharField('礼物名称', max_length=100)
  icon = models.ImageField('礼物图标', upload_to='gifts/icons/', blank=True, null=True)
  price = models.DecimalField('价格（元）', max_digits=10, decimal_places=2)
  heat_value = models.PositiveIntegerField('热度值', help_text='赠送后转换为候选人的热度')
  description = models.CharField('描述', max_length=255, blank=True, default='')
  is_active = models.BooleanField('是否上架', default=True)
  sort_order = models.PositiveIntegerField('排序', default=0)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)

  class Meta:
    verbose_name = '礼物'
    verbose_name_plural = '礼物'
    ordering = ['sort_order', 'price']

  def __str__(self):
    return f'{self.name} (¥{self.price} -> {self.heat_value}热度)'


class GiftTransaction(models.Model):
  """礼物赠送记录。"""

  sender = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='sent_gifts',
    verbose_name='赠送者',
  )
  candidate = models.ForeignKey(
    Candidate,
    on_delete=models.CASCADE,
    related_name='received_gifts',
    verbose_name='接收候选人',
  )
  gift = models.ForeignKey(
    Gift,
    on_delete=models.PROTECT,
    related_name='transactions',
    verbose_name='礼物',
  )
  quantity = models.PositiveIntegerField('数量', default=1)
  total_price = models.DecimalField('总价', max_digits=10, decimal_places=2)
  total_heat = models.PositiveIntegerField('总热度值')
  created_at = models.DateTimeField('赠送时间', auto_now_add=True)

  class Meta:
    verbose_name = '礼物赠送记录'
    verbose_name_plural = '礼物赠送记录'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.sender.phone} 送 {self.gift.name} x{self.quantity} -> {self.candidate.name}'
