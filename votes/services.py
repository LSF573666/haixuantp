from django.db import transaction
from django.db.models import F
from django.utils import timezone

from candidates.models import Candidate
from core.models import SiteConfig
from votes.models import Vote

DAILY_VOTE_LIMIT_KEY = 'daily_vote_limit'


def get_daily_vote_limit():
  return SiteConfig.get_int(DAILY_VOTE_LIMIT_KEY, default=3)


def get_user_today_vote_count(user):
  today = timezone.localdate()
  return Vote.objects.filter(user=user, vote_date=today).count()


def get_user_remaining_votes(user):
  return max(0, get_daily_vote_limit() - get_user_today_vote_count(user))


@transaction.atomic
def cast_vote(user, candidate_id):
  """执行投票，返回 (vote, remaining_votes) 或抛出 ValueError。"""
  today = timezone.localdate()
  daily_limit = get_daily_vote_limit()

  today_count = Vote.objects.filter(user=user, vote_date=today).count()
  if today_count >= daily_limit:
    raise ValueError(f'今日投票次数已用完（每日限{daily_limit}票）')

  try:
    candidate = Candidate.objects.select_for_update().get(pk=candidate_id, is_active=True)
  except Candidate.DoesNotExist:
    raise ValueError('候选人不存在或已下架')

  vote = Vote.objects.create(user=user, candidate=candidate, vote_date=today)
  candidate.vote_count = F('vote_count') + 1
  candidate.heat_score = F('heat_score') + 1
  candidate.save(update_fields=['vote_count', 'heat_score', 'updated_at'])

  remaining = daily_limit - today_count - 1
  return vote, remaining
