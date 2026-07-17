from django.urls import path

from payments.views import (
  AlipayNotifyView,
  AlipayWithdrawNotifyView,
  CreateRechargeView,
  CreateWithdrawView,
  DevPayView,
  OrderDetailView,
  OrderListView,
  PayeeAccountListView,
  WalletBalanceView,
  WeChatNotifyView,
  WeChatWithdrawNotifyView,
  WithdrawListView,
)

urlpatterns = [
  path('wallet/', WalletBalanceView.as_view(), name='wallet-balance'),
  path('recharge/', CreateRechargeView.as_view(), name='create-recharge'),
  path('dev-pay/', DevPayView.as_view(), name='dev-pay'),
  path('orders/', OrderListView.as_view(), name='order-list'),
  path('orders/<str:order_no>/', OrderDetailView.as_view(), name='order-detail'),
  path('payee-accounts/', PayeeAccountListView.as_view(), name='payee-accounts'),
  path('withdraw/', CreateWithdrawView.as_view(), name='create-withdraw'),
  path('withdraws/', WithdrawListView.as_view(), name='withdraw-list'),
  path('wechat/notify/', WeChatNotifyView.as_view(), name='wechat-notify'),
  path('alipay/notify/', AlipayNotifyView.as_view(), name='alipay-notify'),
  path('withdraw/wechat/notify/', WeChatWithdrawNotifyView.as_view(), name='wechat-withdraw-notify'),
  path('withdraw/alipay/notify/', AlipayWithdrawNotifyView.as_view(), name='alipay-withdraw-notify'),
]
