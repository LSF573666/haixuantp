from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import SMSCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
  """后台展示全部平台注册用户（含手机号注册用户与后台账号）。"""

  list_display = [
    'id',
    'phone_display',
    'nickname',
    'balance',
    'is_active',
    'is_staff',
    'created_at',
  ]
  list_filter = [
    'is_active',
    'is_staff',
    'created_at',
  ]
  search_fields = [
    'username', 'phone', 'nickname', 'email',
  ]
  ordering = ['-created_at']
  list_per_page = 50
  date_hierarchy = 'created_at'
  readonly_fields = [
    'created_at', 'updated_at',
    'last_login', 'date_joined',
  ]
  fieldsets = (
    (None, {'fields': ('username', 'password')}),
    ('平台账号', {'fields': ('phone', 'nickname', 'avatar', 'balance')}),
    ('权限', {'fields': (
      'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',
    )}),
    ('重要日期', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
  )
  add_fieldsets = (
    (None, {
      'classes': ('wide',),
      'fields': ('username', 'password1', 'password2', 'phone', 'nickname'),
    }),
  )

  def get_queryset(self, request):
    # 明确列出全部用户，不做 staff / 激活状态筛选
    return super().get_queryset(request)

  @admin.display(description='手机号', ordering='phone')
  def phone_display(self, obj):
    return obj.phone or obj.username or '-'


@admin.register(SMSCode)
class SMSCodeAdmin(admin.ModelAdmin):
  list_display = ['phone', 'code', 'is_used', 'created_at', 'expires_at']
  list_filter = ['is_used', 'created_at']
  search_fields = ['phone']
  readonly_fields = ['phone', 'code', 'is_used', 'created_at', 'expires_at']
