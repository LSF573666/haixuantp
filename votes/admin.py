from django.contrib import admin

from votes.models import Vote


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
  list_display = ['user', 'candidate', 'vote_date', 'created_at']
  list_filter = ['vote_date', 'created_at']
  search_fields = ['user__phone', 'candidate__name']
  readonly_fields = ['user', 'candidate', 'vote_date', 'created_at']
  date_hierarchy = 'vote_date'
