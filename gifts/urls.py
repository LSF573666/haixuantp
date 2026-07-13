from django.urls import path

from gifts.views import GiftHistoryView, GiftListView, SendGiftView

urlpatterns = [
  path('', GiftListView.as_view(), name='gift-list'),
  path('send/', SendGiftView.as_view(), name='send-gift'),
  path('history/', GiftHistoryView.as_view(), name='gift-history'),
]
