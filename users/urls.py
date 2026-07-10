from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import PhoneLoginView, SendSMSCodeView, UserProfileView

urlpatterns = [
  path('sms/send/', SendSMSCodeView.as_view(), name='send-sms'),
  path('login/', PhoneLoginView.as_view(), name='phone-login'),
  path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
  path('profile/', UserProfileView.as_view(), name='user-profile'),
]
