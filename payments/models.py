import uuid

from django.conf import settings
from django.db import models


class PaymentOrder(models.Model):
  """支付订单（充值 / 礼物直付）。"""

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
  def generate_order_no(prefix='ORD'):
    """微信要求商户单号仅字母数字，最长 32。"""
    prefix = ''.join(ch for ch in (prefix or 'ORD') if ch.isalnum()).upper() or 'ORD'
    body_len = max(6, (32 - len(prefix)) // 2)
    return f'{prefix}{uuid.uuid4().hex[:body_len].upper()}'[:32]


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


class PayeeAccount(models.Model):
  """用户提现收款账户（微信 openid / 支付宝登录号）。"""

  class Channel(models.TextChoices):
    WECHAT = 'wechat', '微信'
    ALIPAY = 'alipay', '支付宝'

  user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='payee_accounts',
    verbose_name='用户',
  )
  channel = models.CharField('渠道', max_length=20, choices=Channel.choices)
  account = models.CharField('收款账号', max_length=128)
  account_name = models.CharField('收款人姓名', max_length=64)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)
  updated_at = models.DateTimeField('更新时间', auto_now=True)

  class Meta:
    verbose_name = '收款账户'
    verbose_name_plural = '收款账户'
    ordering = ['channel', '-updated_at']
    constraints = [
      models.UniqueConstraint(fields=['user', 'channel'], name='uniq_payee_user_channel'),
    ]

  def __str__(self):
    return f'{self.user_id}-{self.channel}-{self.account_name}'


class WithdrawOrder(models.Model):
  """提现订单。"""

  class Channel(models.TextChoices):
    WECHAT = 'wechat', '微信'
    ALIPAY = 'alipay', '支付宝'

  class Status(models.TextChoices):
    PENDING = 'pending', '处理中'
    AWAIT_CONFIRM = 'await_confirm', '待用户确认'
    SUCCESS = 'success', '成功'
    FAILED = 'failed', '失败'
    CANCELLED = 'cancelled', '已取消'

  order_no = models.CharField('提现单号', max_length=64, unique=True, db_index=True)
  user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='withdraw_orders',
    verbose_name='用户',
  )
  channel = models.CharField('提现渠道', max_length=20, choices=Channel.choices)
  amount = models.DecimalField('金额', max_digits=10, decimal_places=2)
  status = models.CharField(
    '状态',
    max_length=20,
    choices=Status.choices,
    default=Status.PENDING,
  )
  payee_account = models.CharField('收款账号', max_length=128)
  payee_name = models.CharField('收款人姓名', max_length=64)
  provider_trade_no = models.CharField('第三方单号', max_length=128, blank=True, default='')
  provider_payload = models.JSONField('第三方返回', default=dict, blank=True)
  remark = models.CharField('备注', max_length=255, blank=True, default='')
  completed_at = models.DateTimeField('完成时间', null=True, blank=True)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)
  updated_at = models.DateTimeField('更新时间', auto_now=True)

  class Meta:
    verbose_name = '提现订单'
    verbose_name_plural = '提现订单'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.order_no} ¥{self.amount} {self.status}'

  @staticmethod
  def generate_order_no():
    return PaymentOrder.generate_order_no(prefix='WD')
