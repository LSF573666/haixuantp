from django.urls import path

from gifts.views import GiftHistoryView, GiftListView, PayGiftView, SendGiftView

urlpatterns = [
  path('', GiftListView.as_view(), name='gift-list'),
  path('send/', SendGiftView.as_view(), name='send-gift'),
  path('pay/', PayGiftView.as_view(), name='pay-gift'),
  path('history/', GiftHistoryView.as_view(), name='gift-history'),
]
