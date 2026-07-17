from django.contrib import admin

from payments.models import PayeeAccount, PaymentOrder, PaymentRecord, WithdrawOrder


class PaymentRecordInline(admin.TabularInline):
  model = PaymentRecord
  extra = 0
  readonly_fields = ['transaction_id', 'payment_method', 'raw_data', 'created_at']


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
  list_display = ['order_no', 'user', 'order_type', 'payment_method', 'amount', 'status', 'created_at']
  list_filter = ['order_type', 'payment_method', 'status', 'created_at']
  search_fields = ['order_no', 'user__phone']
  readonly_fields = [
    'order_no', 'user', 'order_type', 'amount', 'extra_data',
    'paid_at', 'created_at', 'updated_at',
  ]
  inlines = [PaymentRecordInline]


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
  list_display = ['order', 'transaction_id', 'payment_method', 'created_at']
  list_filter = ['payment_method', 'created_at']
  search_fields = ['order__order_no', 'transaction_id']
  readonly_fields = ['order', 'transaction_id', 'payment_method', 'raw_data', 'created_at']


@admin.register(PayeeAccount)
class PayeeAccountAdmin(admin.ModelAdmin):
  list_display = ['user', 'channel', 'account', 'account_name', 'updated_at']
  list_filter = ['channel']
  search_fields = ['user__phone', 'account', 'account_name']


@admin.register(WithdrawOrder)
class WithdrawOrderAdmin(admin.ModelAdmin):
  list_display = [
    'order_no', 'user', 'channel', 'amount', 'status',
    'payee_name', 'created_at', 'completed_at',
  ]
  list_filter = ['channel', 'status', 'created_at']
  search_fields = ['order_no', 'user__phone', 'payee_account', 'provider_trade_no']
  readonly_fields = [
    'order_no', 'user', 'channel', 'amount', 'payee_account', 'payee_name',
    'provider_trade_no', 'provider_payload', 'completed_at', 'created_at', 'updated_at',
  ]
