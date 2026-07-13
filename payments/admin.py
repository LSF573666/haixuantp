from django.contrib import admin

from payments.models import PaymentOrder, PaymentRecord


class PaymentRecordInline(admin.TabularInline):
  model = PaymentRecord
  extra = 0
  readonly_fields = ['transaction_id', 'payment_method', 'raw_data', 'created_at']


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
  list_display = ['order_no', 'user', 'order_type', 'payment_method', 'amount', 'status', 'created_at']
  list_filter = ['order_type', 'payment_method', 'status', 'created_at']
  search_fields = ['order_no', 'user__phone']
  readonly_fields = ['order_no', 'user', 'order_type', 'amount', 'paid_at', 'created_at', 'updated_at']
  inlines = [PaymentRecordInline]


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
  list_display = ['order', 'transaction_id', 'payment_method', 'created_at']
  list_filter = ['payment_method', 'created_at']
  search_fields = ['order__order_no', 'transaction_id']
  readonly_fields = ['order', 'transaction_id', 'payment_method', 'raw_data', 'created_at']
