from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from candidates.models import Candidate
from gifts.models import Gift, GiftTransaction
from payments.gateway import (
  create_payment_order,
  create_payout_transfer,
  parse_alipay_notify,
  parse_wechat_notify,
  wechat_transfer_confirm_payload,
)
from payments.models import PayeeAccount, PaymentOrder, PaymentRecord, WithdrawOrder


MIN_AMOUNT = Decimal('0.01')
MIN_WITHDRAW = Decimal('0.01')


def _quantize(amount) -> Decimal:
  return Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _mask_account(account: str) -> str:
  text = (account or '').strip()
  if not text:
    return ''
  if '@' in text:
    local, domain = text.split('@', 1)
    if len(local) <= 2:
      return f'{local[0]}***@{domain}'
    return f'{local[:2]}***@{domain}'
  if len(text) <= 7:
    return f'{text[0]}***'
  return f'{text[:3]}****{text[-4:]}'


def _pay_notify_url(channel: str) -> str:
  if channel == 'wechat':
    return (getattr(settings, 'WECHAT_PAY_NOTIFY_URL', '') or '').strip()
  return (getattr(settings, 'ALIPAY_NOTIFY_URL', '') or '').strip()


def _withdraw_notify_url(channel: str) -> str:
  if channel == 'wechat':
    return (getattr(settings, 'WECHAT_PAY_WITHDRAW_NOTIFY_URL', '') or '').strip()
  return (getattr(settings, 'ALIPAY_WITHDRAW_NOTIFY_URL', '') or '').strip()


def _build_pay_data(order: PaymentOrder, description: str) -> dict:
  notify_url = _pay_notify_url(order.payment_method)
  if not notify_url:
    return {
      'dev_mode': True,
      'order_no': order.order_no,
      'amount': str(order.amount),
      'message': '未配置支付回调地址，开发环境请使用 /api/payments/dev-pay/',
    }

  configured = bool(
    (order.payment_method == 'wechat' and settings.WECHAT_PAY_APP_ID)
    or (order.payment_method == 'alipay' and settings.ALIPAY_APP_ID)
  )
  if not configured:
    return {
      'dev_mode': True,
      'order_no': order.order_no,
      'amount': str(order.amount),
      'message': '支付未配置，开发环境请使用 /api/payments/dev-pay/',
    }

  result = create_payment_order(
    channel=order.payment_method,
    out_trade_no=order.order_no,
    amount=order.amount,
    notify_url=notify_url,
    description=description,
  )
  if not result.ok:
    raise ValueError(result.message or '创建支付失败')

  pay_data = {
    'order_no': order.order_no,
    'payment_mode': result.payment_mode,
    'code_url': result.payment_url,
    'qr_code': result.payment_url,
    'expires_at': result.expires_at.isoformat() if result.expires_at else None,
  }
  if result.provider_payload:
    order.extra_data = {
      **(order.extra_data or {}),
      'provider_payload': result.provider_payload,
    }
    order.save(update_fields=['extra_data', 'updated_at'])
  return pay_data


@transaction.atomic
def create_recharge_order(user, amount, payment_method):
  """创建充值订单并发起第三方支付。"""
  amount = _quantize(amount)
  if amount < MIN_AMOUNT:
    raise ValueError('充值金额必须大于0')
  if payment_method not in (PaymentOrder.PaymentMethod.WECHAT, PaymentOrder.PaymentMethod.ALIPAY):
    raise ValueError('不支持的支付方式')

  order = PaymentOrder.objects.create(
    order_no=PaymentOrder.generate_order_no('RC'),
    user=user,
    order_type=PaymentOrder.OrderType.RECHARGE,
    payment_method=payment_method,
    amount=amount,
    status=PaymentOrder.Status.PENDING,
  )
  pay_data = _build_pay_data(order, description=f'账户充值-{order.order_no}')
  return order, pay_data


@transaction.atomic
def create_gift_payment_order(user, candidate_id, gift_id, quantity, payment_method):
  """创建礼物直付订单（微信/支付宝扫码支付成功后赠送）。"""
  if quantity < 1:
    raise ValueError('数量必须大于0')
  if payment_method not in (PaymentOrder.PaymentMethod.WECHAT, PaymentOrder.PaymentMethod.ALIPAY):
    raise ValueError('不支持的支付方式')

  try:
    gift = Gift.objects.get(pk=gift_id, is_active=True)
  except Gift.DoesNotExist:
    raise ValueError('礼物不存在或已下架')

  try:
    candidate = Candidate.objects.get(pk=candidate_id, is_active=True)
  except Candidate.DoesNotExist:
    raise ValueError('候选人不存在或已下架')

  total_price = _quantize(gift.price * quantity)
  if total_price < MIN_AMOUNT:
    raise ValueError('支付金额无效')

  order = PaymentOrder.objects.create(
    order_no=PaymentOrder.generate_order_no('GF'),
    user=user,
    order_type=PaymentOrder.OrderType.GIFT,
    payment_method=payment_method,
    amount=total_price,
    status=PaymentOrder.Status.PENDING,
    extra_data={
      'candidate_id': candidate.id,
      'gift_id': gift.id,
      'quantity': quantity,
      'gift_name': gift.name,
      'candidate_name': candidate.name,
    },
  )
  pay_data = _build_pay_data(order, description=f'礼物-{gift.name}')
  return order, pay_data


def _fulfill_gift_order(order: PaymentOrder):
  """支付成功后发放礼物（不扣余额）。"""
  extra = order.extra_data or {}
  if extra.get('fulfilled'):
    return None

  gift_id = extra.get('gift_id')
  candidate_id = extra.get('candidate_id')
  quantity = int(extra.get('quantity') or 1)
  if not gift_id or not candidate_id:
    raise ValueError('礼物订单缺少附加数据')

  gift = Gift.objects.select_for_update().get(pk=gift_id)
  candidate = Candidate.objects.select_for_update().get(pk=candidate_id)
  total_heat = gift.heat_value * quantity

  candidate.heat_score = F('heat_score') + total_heat
  candidate.save(update_fields=['heat_score', 'updated_at'])

  record = GiftTransaction.objects.create(
    sender=order.user,
    candidate=candidate,
    gift=gift,
    quantity=quantity,
    total_price=order.amount,
    total_heat=total_heat,
  )
  order.extra_data = {**extra, 'fulfilled': True, 'gift_transaction_id': record.id}
  order.save(update_fields=['extra_data', 'updated_at'])
  return record


@transaction.atomic
def complete_order(order, transaction_id='', raw_data=None):
  """完成支付订单：充值入账，或礼物直付发货。"""
  order = PaymentOrder.objects.select_for_update().get(pk=order.pk)
  if order.status == PaymentOrder.Status.PAID:
    return order

  order.status = PaymentOrder.Status.PAID
  order.paid_at = timezone.now()
  order.save(update_fields=['status', 'paid_at', 'updated_at'])

  if order.order_type == PaymentOrder.OrderType.RECHARGE:
    user = type(order.user).objects.select_for_update().get(pk=order.user_id)
    user.balance = F('balance') + order.amount
    user.save(update_fields=['balance', 'updated_at'])
  elif order.order_type == PaymentOrder.OrderType.GIFT:
    _fulfill_gift_order(order)

  if transaction_id or raw_data:
    PaymentRecord.objects.create(
      order=order,
      transaction_id=transaction_id or '',
      payment_method=order.payment_method,
      raw_data=raw_data or {},
    )
  return order


def handle_payment_notify(*, channel: str, request=None, post_data=None):
  """处理微信/支付宝支付回调，返回 (ok, response_body, http_content_type)。"""
  if channel == 'wechat':
    parsed = parse_wechat_notify(request)
    fail_body = {'code': 'FAIL', 'message': parsed.message}
    ok_body = {'code': 'SUCCESS', 'message': '成功'}
  else:
    parsed = parse_alipay_notify(post_data or {})
    fail_body = 'fail'
    ok_body = 'success'

  if not parsed.ok:
    return False, fail_body if channel == 'wechat' else fail_body, parsed.message

  if not parsed.paid:
    return True, ok_body, 'not_paid'

  try:
    order = PaymentOrder.objects.get(order_no=parsed.out_trade_no)
  except PaymentOrder.DoesNotExist:
    return True, ok_body, 'order_not_found'

  if order.status == PaymentOrder.Status.PAID:
    return True, ok_body, 'already_paid'

  if order.payment_method and order.payment_method != channel:
    return False, fail_body, 'channel_mismatch'

  complete_order(
    order,
    transaction_id=parsed.provider_trade_no,
    raw_data=parsed.raw_payload or {},
  )
  return True, ok_body, 'ok'


def bind_payee_account(user, *, channel: str, account: str, account_name: str) -> PayeeAccount:
  if channel not in (PayeeAccount.Channel.WECHAT, PayeeAccount.Channel.ALIPAY):
    raise ValueError('不支持的收款渠道')
  account = (account or '').strip()
  account_name = (account_name or '').strip()
  if not account:
    raise ValueError('请填写收款账号')
  if not account_name:
    raise ValueError('请填写收款人姓名')

  row, _ = PayeeAccount.objects.update_or_create(
    user=user,
    channel=channel,
    defaults={
      'account': account[:128],
      'account_name': account_name[:64],
    },
  )
  return row


def unbind_payee_account(user, *, channel: str) -> bool:
  deleted, _ = PayeeAccount.objects.filter(user=user, channel=channel).delete()
  return bool(deleted)


def payee_account_to_dict(row: PayeeAccount, *, mask: bool = True) -> dict:
  return {
    'channel': row.channel,
    'account': _mask_account(row.account) if mask else row.account,
    'account_name': row.account_name,
    'updated_at': row.updated_at.isoformat() if row.updated_at else None,
  }


@transaction.atomic
def create_withdraw_order(user, *, amount, channel: str):
  """创建提现：扣减余额并发起微信/支付宝转账。"""
  amount = _quantize(amount)
  if amount < MIN_WITHDRAW:
    raise ValueError('提现金额必须大于0')
  if channel not in (WithdrawOrder.Channel.WECHAT, WithdrawOrder.Channel.ALIPAY):
    raise ValueError('不支持的提现渠道')

  try:
    payee = PayeeAccount.objects.get(user=user, channel=channel)
  except PayeeAccount.DoesNotExist:
    raise ValueError('请先绑定对应渠道的收款账户')

  locked_user = type(user).objects.select_for_update().get(pk=user.pk)
  if locked_user.balance < amount:
    raise ValueError(f'余额不足，当前余额 ¥{locked_user.balance}')

  locked_user.balance = F('balance') - amount
  locked_user.save(update_fields=['balance', 'updated_at'])

  order = WithdrawOrder.objects.create(
    order_no=WithdrawOrder.generate_order_no(),
    user=locked_user,
    channel=channel,
    amount=amount,
    status=WithdrawOrder.Status.PENDING,
    payee_account=payee.account,
    payee_name=payee.account_name,
  )

  result = create_payout_transfer(
    channel=channel,
    out_biz_no=order.order_no,
    amount=amount,
    payee_account=payee.account,
    payee_name=payee.account_name,
    notify_url=_withdraw_notify_url(channel),
  )

  if not result.ok:
    locked_user.refresh_from_db(fields=['balance'])
    locked_user.balance = F('balance') + amount
    locked_user.save(update_fields=['balance', 'updated_at'])
    order.status = WithdrawOrder.Status.FAILED
    order.remark = (result.message or 'transfer_failed')[:255]
    order.provider_payload = result.provider_payload or {}
    order.completed_at = timezone.now()
    order.save(update_fields=[
      'status', 'remark', 'provider_payload', 'completed_at', 'updated_at',
    ])
    raise ValueError(result.message or '提现发起失败')

  order.provider_trade_no = result.provider_trade_no or ''
  order.provider_payload = result.provider_payload or {}
  confirm = wechat_transfer_confirm_payload(result.provider_payload)

  if result.pending_user_confirm:
    order.status = WithdrawOrder.Status.AWAIT_CONFIRM
    order.remark = 'await_user_confirm'
    order.save(update_fields=[
      'provider_trade_no', 'provider_payload', 'status', 'remark', 'updated_at',
    ])
    return order, confirm

  if channel == 'alipay' and not _withdraw_notify_url(channel):
    # 支付宝转账一般为实时成功；无回调时直接置成功
    order.status = WithdrawOrder.Status.SUCCESS
    order.completed_at = timezone.now()
    order.remark = 'alipay_transfer_ok'
    order.save(update_fields=[
      'provider_trade_no', 'provider_payload', 'status', 'completed_at', 'remark', 'updated_at',
    ])
  else:
    order.save(update_fields=['provider_trade_no', 'provider_payload', 'updated_at'])

  return order, confirm


@transaction.atomic
def complete_withdraw_order(order: WithdrawOrder, *, remark: str = ''):
  order = WithdrawOrder.objects.select_for_update().get(pk=order.pk)
  if order.status == WithdrawOrder.Status.SUCCESS:
    return order
  if order.status == WithdrawOrder.Status.FAILED:
    return order

  order.status = WithdrawOrder.Status.SUCCESS
  order.completed_at = timezone.now()
  if remark:
    order.remark = remark[:255]
  order.save(update_fields=['status', 'completed_at', 'remark', 'updated_at'])
  return order


@transaction.atomic
def fail_withdraw_order(order: WithdrawOrder, *, remark: str = ''):
  """提现失败：退回余额。"""
  order = WithdrawOrder.objects.select_for_update().get(pk=order.pk)
  if order.status in (WithdrawOrder.Status.SUCCESS, WithdrawOrder.Status.FAILED):
    return order

  user = type(order.user).objects.select_for_update().get(pk=order.user_id)
  user.balance = F('balance') + order.amount
  user.save(update_fields=['balance', 'updated_at'])

  order.status = WithdrawOrder.Status.FAILED
  order.completed_at = timezone.now()
  order.remark = (remark or 'failed')[:255]
  order.save(update_fields=['status', 'completed_at', 'remark', 'updated_at'])
  return order


def handle_withdraw_notify(*, channel: str, request=None, post_data=None):
  if channel == 'wechat':
    parsed = parse_wechat_notify(request)
    fail_body = {'code': 'FAIL', 'message': parsed.message}
    ok_body = {'code': 'SUCCESS', 'message': '成功'}
  else:
    parsed = parse_alipay_notify(post_data or {})
    fail_body = 'fail'
    ok_body = 'success'

  if not parsed.ok:
    return False, fail_body, parsed.message

  try:
    order = WithdrawOrder.objects.get(order_no=parsed.out_trade_no)
  except WithdrawOrder.DoesNotExist:
    return True, ok_body, 'order_not_found'

  if parsed.provider_trade_no:
    order.provider_trade_no = parsed.provider_trade_no
  if parsed.raw_payload:
    order.provider_payload = {**(order.provider_payload or {}), **parsed.raw_payload}
  order.save(update_fields=['provider_trade_no', 'provider_payload', 'updated_at'])

  state = ''
  if parsed.raw_payload:
    state = str(parsed.raw_payload.get('state') or parsed.raw_payload.get('status') or '').upper()

  if parsed.paid or state in ('SUCCESS', 'TRADE_SUCCESS'):
    complete_withdraw_order(order, remark='notify_success')
  elif state in ('FAIL', 'FAILED', 'CLOSED', 'CANCELLED', 'REVOKED'):
    fail_withdraw_order(order, remark=f'notify_{state.lower()}')

  return True, ok_body, 'ok'


# 兼容旧视图命名
class WeChatPayService:
  @staticmethod
  def create_order(order):
    return _build_pay_data(order, description=f'账户充值-{order.order_no}')

  @staticmethod
  def verify_notify(data):
    return True


class AlipayService:
  @staticmethod
  def create_order(order):
    return _build_pay_data(order, description=f'账户充值-{order.order_no}')

  @staticmethod
  def verify_notify(data):
    return True
