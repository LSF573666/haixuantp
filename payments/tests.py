from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from payments.gateway import NotifyParseResult
from payments.models import PaymentOrder, PaymentRecord
from payments.services import complete_order, handle_payment_notify

User = get_user_model()

TEST_MIDDLEWARE = [
  'django.middleware.security.SecurityMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.middleware.common.CommonMiddleware',
  'django.middleware.csrf.CsrfViewMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class AlipayRechargeNotifyTests(APITestCase):
  def setUp(self):
    self.user = User.objects.create_user(
      username='13800138000',
      phone='13800138000',
      password='pass',
    )
    self.user.balance = Decimal('0.00')
    self.user.save(update_fields=['balance'])
    self.order = PaymentOrder.objects.create(
      order_no='RCTESTNOTIFY001',
      user=self.user,
      order_type=PaymentOrder.OrderType.RECHARGE,
      payment_method=PaymentOrder.PaymentMethod.ALIPAY,
      amount=Decimal('0.10'),
      status=PaymentOrder.Status.PENDING,
    )

  def test_complete_order_marks_recharge_paid(self):
    complete_order(self.order, transaction_id='ALI123', raw_data={'trade_status': 'TRADE_SUCCESS'})
    self.order.refresh_from_db()
    self.user.refresh_from_db()
    self.assertEqual(self.order.status, PaymentOrder.Status.PAID)
    self.assertEqual(self.order.get_status_display(), '已充值')
    self.assertEqual(self.user.balance, Decimal('0.10'))
    self.assertTrue(PaymentRecord.objects.filter(order=self.order).exists())

  @patch('payments.services.parse_alipay_notify')
  def test_alipay_notify_sets_paid_not_pending(self, mock_parse):
    mock_parse.return_value = NotifyParseResult(
      ok=True,
      message='ok',
      out_trade_no=self.order.order_no,
      provider_trade_no='202607210001',
      paid=True,
      raw_payload={'trade_status': 'TRADE_SUCCESS', 'out_trade_no': self.order.order_no},
    )
    ok, body, detail = handle_payment_notify(
      channel='alipay',
      post_data={'out_trade_no': self.order.order_no, 'trade_status': 'TRADE_SUCCESS'},
    )
    self.assertTrue(ok)
    self.assertEqual(body, 'success')
    self.assertEqual(detail, 'ok')
    self.order.refresh_from_db()
    self.user.refresh_from_db()
    self.assertEqual(self.order.status, PaymentOrder.Status.PAID)
    self.assertEqual(self.order.get_status_display(), '已充值')
    self.assertEqual(self.user.balance, Decimal('0.10'))

  @patch('payments.services.query_alipay_trade')
  def test_order_detail_syncs_paid_alipay_trade(self, mock_query):
    mock_query.return_value = NotifyParseResult(
      ok=True,
      message='TRADE_SUCCESS',
      out_trade_no=self.order.order_no,
      provider_trade_no='202607210002',
      paid=True,
      raw_payload={'trade_status': 'TRADE_SUCCESS'},
    )
    self.client.force_authenticate(user=self.user)
    response = self.client.get(reverse('order-detail', kwargs={'order_no': self.order.order_no}))
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data['order']['status'], 'paid')
    self.assertEqual(response.data['order']['status_display'], '已充值')
    self.assertEqual(response.data['balance'], '0.10')
    self.order.refresh_from_db()
    self.assertEqual(self.order.status, PaymentOrder.Status.PAID)
