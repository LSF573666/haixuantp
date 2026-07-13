from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import SMSCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
  list_display = ['username', 'phone', 'nickname', 'is_staff', 'balance', 'is_active', 'created_at']
  list_filter = ['is_active', 'is_staff', 'created_at']
  search_fields = ['username', 'phone', 'nickname']
  ordering = ['-created_at']
  fieldsets = BaseUserAdmin.fieldsets + (
    ('扩展信息', {'fields': ('phone', 'nickname', 'avatar', 'balance')}),
  )
  add_fieldsets = BaseUserAdmin.add_fieldsets + (
    ('扩展信息', {'fields': ('phone', 'nickname')}),
  )


@admin.register(SMSCode)
class SMSCodeAdmin(admin.ModelAdmin):
  list_display = ['phone', 'code', 'is_used', 'created_at', 'expires_at']
  list_filter = ['is_used', 'created_at']
  search_fields = ['phone']
  readonly_fields = ['phone', 'code', 'is_used', 'created_at', 'expires_at']
