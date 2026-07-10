from django.urls import path

from votes.views import CastVoteView, VoteHistoryView, VoteStatusView

urlpatterns = [
  path('status/', VoteStatusView.as_view(), name='vote-status'),
  path('cast/', CastVoteView.as_view(), name='cast-vote'),
  path('history/', VoteHistoryView.as_view(), name='vote-history'),
]
