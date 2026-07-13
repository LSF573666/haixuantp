from django.urls import path

from candidates.views import (
  CandidateApplicationStatusView,
  CandidateApplicationSubmitView,
  CandidateDetailView,
  CandidateListView,
  CandidateRankingView,
)

urlpatterns = [
  path('', CandidateListView.as_view(), name='candidate-list'),
  path('ranking/', CandidateRankingView.as_view(), name='candidate-ranking'),
  path('applications/submit/', CandidateApplicationSubmitView.as_view(), name='candidate-application-submit'),
  path('applications/status/', CandidateApplicationStatusView.as_view(), name='candidate-application-status'),
  path('<int:pk>/', CandidateDetailView.as_view(), name='candidate-detail'),
]
