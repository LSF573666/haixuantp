from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
  help = '创建后台管理员账号（username + 密码登录）'

  def add_arguments(self, parser):
    parser.add_argument('--username', default='admin', help='管理员用户名，默认 admin')
    parser.add_argument('--password', default='admin123', help='管理员密码，默认 admin123')

  def handle(self, *args, **options):
    User = get_user_model()
    username = options['username']
    password = options['password']

    if User.objects.filter(username=username).exists():
      self.stdout.write(self.style.WARNING(f'用户 {username} 已存在，跳过创建'))
      return

    User.objects.create_superuser(username=username, password=password)
    self.stdout.write(self.style.SUCCESS(
      f'管理员已创建: 用户名={username}，密码={password}，请登录 http://localhost:8000/admin/'
    ))
