import hashlib
import time
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from payments.models import PaymentOrder, PaymentRecord


@transaction.atomic
def create_recharge_order(user, amount, payment_method):
  """创建充值订单。"""
  if amount <= 0:
    raise ValueError('充值金额必须大于0')

  order = PaymentOrder.objects.create(
    order_no=PaymentOrder.generate_order_no(),
    user=user,
    order_type=PaymentOrder.OrderType.RECHARGE,
    payment_method=payment_method,
    amount=amount,
    status=PaymentOrder.Status.PENDING,
  )
  return order


@transaction.atomic
def complete_order(order, transaction_id='', raw_data=None):
  """完成订单支付，充值到用户余额。"""
  order = PaymentOrder.objects.select_for_update().get(pk=order.pk)
  if order.status == PaymentOrder.Status.PAID:
    return order

  order.status = PaymentOrder.Status.PAID
  order.paid_at = timezone.now()
  order.save(update_fields=['status', 'paid_at', 'updated_at'])

  if order.order_type == PaymentOrder.OrderType.RECHARGE:
    user = order.user
    user.balance = F('balance') + order.amount
    user.save(update_fields=['balance', 'updated_at'])

  if transaction_id or raw_data:
    PaymentRecord.objects.create(
      order=order,
      transaction_id=transaction_id or '',
      payment_method=order.payment_method,
      raw_data=raw_data or {},
    )
  return order


class WeChatPayService:
  """微信支付服务（统一下单）。"""

  @staticmethod
  def create_order(order):
    if not settings.WECHAT_APP_ID:
      return {
        'dev_mode': True,
        'order_no': order.order_no,
        'amount': str(order.amount),
        'message': '微信支付未配置，开发模式下请调用模拟支付接口',
      }

    nonce_str = uuid.uuid4().hex
    params = {
      'appid': settings.WECHAT_APP_ID,
      'mch_id': settings.WECHAT_MCH_ID,
      'nonce_str': nonce_str,
      'body': f'账户充值-{order.order_no}',
      'out_trade_no': order.order_no,
      'total_fee': int(order.amount * 100),
      'spbill_create_ip': '127.0.0.1',
      'notify_url': settings.WECHAT_NOTIFY_URL,
      'trade_type': 'JSAPI',
    }
    # 实际生产环境需要调用微信统一下单 API 并返回 prepay_id
    return {
      'order_no': order.order_no,
      'prepay_params': params,
      'message': '请配置完整的微信支付参数后使用',
    }

  @staticmethod
  def verify_notify(data):
    # 实际生产环境需验证签名
    return True


class AlipayService:
  """支付宝支付服务。"""

  @staticmethod
  def create_order(order):
    if not settings.ALIPAY_APP_ID:
      return {
        'dev_mode': True,
        'order_no': order.order_no,
        'amount': str(order.amount),
        'message': '支付宝未配置，开发模式下请调用模拟支付接口',
      }

    return {
      'order_no': order.order_no,
      'pay_url': f'https://openapi.alipay.com/gateway.do?out_trade_no={order.order_no}',
      'message': '请配置完整的支付宝参数后使用',
    }

  @staticmethod
  def verify_notify(data):
    return True
