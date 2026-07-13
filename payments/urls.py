from django.urls import path

from payments.views import (
  AlipayNotifyView,
  CreateRechargeView,
  DevPayView,
  OrderListView,
  WeChatNotifyView,
)

urlpatterns = [
  path('recharge/', CreateRechargeView.as_view(), name='create-recharge'),
  path('dev-pay/', DevPayView.as_view(), name='dev-pay'),
  path('orders/', OrderListView.as_view(), name='order-list'),
  path('wechat/notify/', WeChatNotifyView.as_view(), name='wechat-notify'),
  path('alipay/notify/', AlipayNotifyView.as_view(), name='alipay-notify'),
]
