from django.urls import path

from core.views import PublicConfigView

urlpatterns = [
  path('public/', PublicConfigView.as_view(), name='public-config'),
]
