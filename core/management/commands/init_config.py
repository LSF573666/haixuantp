from django.core.management.base import BaseCommand

from core.models import SiteConfig


class Command(BaseCommand):
  help = '初始化系统默认配置'

  def handle(self, *args, **options):
    defaults = [
      ('daily_vote_limit', '3', '每人每天可投票次数'),
    ]
    for key, value, description in defaults:
      SiteConfig.set_value(key, value, description)
      self.stdout.write(self.style.SUCCESS(f'配置已设置: {key} = {value}'))
    self.stdout.write(self.style.SUCCESS('初始化完成'))
