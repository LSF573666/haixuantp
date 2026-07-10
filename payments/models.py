import uuid

from django.conf import settings
from django.db import models


class PaymentOrder(models.Model):
  """支付订单。"""

  class OrderType(models.TextChoices):
    RECHARGE = 'recharge', '充值'
    GIFT = 'gift', '购买礼物'

  class PaymentMethod(models.TextChoices):
    WECHAT = 'wechat', '微信支付'
    ALIPAY = 'alipay', '支付宝'
    BALANCE = 'balance', '余额支付'

  class Status(models.TextChoices):
    PENDING = 'pending', '待支付'
    PAID = 'paid', '已支付'
    FAILED = 'failed', '支付失败'
    CANCELLED = 'cancelled', '已取消'
    REFUNDED = 'refunded', '已退款'

  order_no = models.CharField('订单号', max_length=64, unique=True, db_index=True)
  user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='orders',
    verbose_name='用户',
  )
  order_type = models.CharField('订单类型', max_length=20, choices=OrderType.choices)
  payment_method = models.CharField(
    '支付方式',
    max_length=20,
    choices=PaymentMethod.choices,
    blank=True,
    default='',
  )
  amount = models.DecimalField('金额', max_digits=10, decimal_places=2)
  status = models.CharField(
    '状态',
    max_length=20,
    choices=Status.choices,
    default=Status.PENDING,
  )
  extra_data = models.JSONField('附加数据', default=dict, blank=True)
  paid_at = models.DateTimeField('支付时间', null=True, blank=True)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)
  updated_at = models.DateTimeField('更新时间', auto_now=True)

  class Meta:
    verbose_name = '支付订单'
    verbose_name_plural = '支付订单'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.order_no} - {self.get_order_type_display()} ¥{self.amount}'

  @staticmethod
  def generate_order_no():
    return f'ORD{uuid.uuid4().hex[:20].upper()}'


class PaymentRecord(models.Model):
  """第三方支付回调记录。"""

  order = models.ForeignKey(
    PaymentOrder,
    on_delete=models.CASCADE,
    related_name='payment_records',
    verbose_name='订单',
  )
  transaction_id = models.CharField('第三方交易号', max_length=128, blank=True, default='')
  payment_method = models.CharField('支付方式', max_length=20)
  raw_data = models.JSONField('原始回调数据', default=dict)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)

  class Meta:
    verbose_name = '支付记录'
    verbose_name_plural = '支付记录'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.order.order_no} - {self.transaction_id}'
