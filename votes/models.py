from django.conf import settings
from django.db import models

from candidates.models import Candidate


class Vote(models.Model):
  """投票记录。"""

  user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='votes',
    verbose_name='投票用户',
  )
  candidate = models.ForeignKey(
    Candidate,
    on_delete=models.CASCADE,
    related_name='votes',
    verbose_name='候选人',
  )
  vote_date = models.DateField('投票日期', db_index=True)
  created_at = models.DateTimeField('投票时间', auto_now_add=True)

  class Meta:
    verbose_name = '投票记录'
    verbose_name_plural = '投票记录'
    ordering = ['-created_at']
    indexes = [
      models.Index(fields=['user', 'vote_date']),
      models.Index(fields=['candidate', 'vote_date']),
    ]

  def __str__(self):
    return f'{self.user.phone} -> {self.candidate.name} ({self.vote_date})'
