from django.contrib import admin

from gifts.models import Gift, GiftTransaction


@admin.register(Gift)
class GiftAdmin(admin.ModelAdmin):
  list_display = ['name', 'price', 'heat_value', 'is_active', 'sort_order', 'created_at']
  list_filter = ['is_active']
  search_fields = ['name']


@admin.register(GiftTransaction)
class GiftTransactionAdmin(admin.ModelAdmin):
  list_display = ['sender', 'candidate', 'gift', 'quantity', 'total_price', 'total_heat', 'created_at']
  list_filter = ['created_at']
  search_fields = ['sender__phone', 'candidate__name', 'gift__name']
  readonly_fields = ['sender', 'candidate', 'gift', 'quantity', 'total_price', 'total_heat', 'created_at']
