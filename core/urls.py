from django.urls import path

from core.views import OSSStsCredentialView, PublicConfigView

urlpatterns = [
  path('public/', PublicConfigView.as_view(), name='public-config'),
  path('oss/sts/', OSSStsCredentialView.as_view(), name='oss-sts'),
]
