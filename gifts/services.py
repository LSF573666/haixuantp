from django.db import transaction
from django.db.models import F

from candidates.models import Candidate
from gifts.models import Gift, GiftTransaction


@transaction.atomic
def send_gift(user, candidate_id, gift_id, quantity=1):
  """使用余额购买并赠送礼物。返回 GiftTransaction 或抛出 ValueError。"""
  if quantity < 1:
    raise ValueError('数量必须大于0')

  try:
    gift = Gift.objects.get(pk=gift_id, is_active=True)
  except Gift.DoesNotExist:
    raise ValueError('礼物不存在或已下架')

  try:
    candidate = Candidate.objects.select_for_update().get(pk=candidate_id, is_active=True)
  except Candidate.DoesNotExist:
    raise ValueError('候选人不存在或已下架')

  total_price = gift.price * quantity
  total_heat = gift.heat_value * quantity

  user = type(user).objects.select_for_update().get(pk=user.pk)
  if user.balance < total_price:
    raise ValueError(f'余额不足，需要 ¥{total_price}，当前余额 ¥{user.balance}')

  user.balance = F('balance') - total_price
  user.save(update_fields=['balance', 'updated_at'])

  candidate.heat_score = F('heat_score') + total_heat
  candidate.save(update_fields=['heat_score', 'updated_at'])

  transaction_record = GiftTransaction.objects.create(
    sender=user,
    candidate=candidate,
    gift=gift,
    quantity=quantity,
    total_price=total_price,
    total_heat=total_heat,
  )
  user.refresh_from_db(fields=['balance'])
  candidate.refresh_from_db(fields=['heat_score'])
  return transaction_record
