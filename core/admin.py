from django.contrib import admin

from core.models import FrontendRequestLog, SiteConfig


@admin.register(FrontendRequestLog)
class FrontendRequestLogAdmin(admin.ModelAdmin):
  list_display = [
    'created_at',
    'method',
    'path',
    'status_code',
    'duration_ms',
    'user',
    'ip_address',
  ]
  list_filter = ['method', 'status_code', 'created_at']
  search_fields = ['path', 'ip_address', 'user__phone', 'user__username']
  readonly_fields = [
    'user',
    'method',
    'path',
    'query_string',
    'request_body',
    'status_code',
    'duration_ms',
    'ip_address',
    'user_agent',
    'created_at',
  ]
  date_hierarchy = 'created_at'
  ordering = ['-created_at']

  def has_add_permission(self, request):
    return False

  def has_change_permission(self, request, obj=None):
    return False


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
  list_display = ['key', 'value', 'description', 'updated_at']
  search_fields = ['key', 'description']
  list_editable = ['value', 'description']
