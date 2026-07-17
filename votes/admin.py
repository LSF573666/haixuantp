from django.contrib import admin

from votes.models import Vote


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
  list_display = ['user', 'candidate', 'vote_date', 'created_at']
  list_filter = ['vote_date', 'created_at']
  search_fields = ['user__phone', 'candidate__name']
  readonly_fields = ['user', 'candidate', 'vote_date', 'created_at']
  date_hierarchy = 'vote_date'

  def has_add_permission(self, request):
    # 投票只能通过业务接口创建，后台不可手工新增
    return False
