from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

admin.site.site_header = '海选投票系统'
admin.site.site_title = '海选投票系统'
admin.site.index_title = '管理后台'

urlpatterns = [
    path('admin/', admin.site.urls),
    # API（推荐带 /api/ 前缀）
    path('api/auth/', include('users.urls')),
    path('api/candidates/', include('candidates.urls')),
    path('api/votes/', include('votes.urls')),
    path('api/gifts/', include('gifts.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/config/', include('core.urls')),
    # 兼容无前缀访问
    path('auth/', include('users.urls')),
    path('candidates/', include('candidates.urls')),
    path('votes/', include('votes.urls')),
    path('gifts/', include('gifts.urls')),
    path('payments/', include('payments.urls')),
    path('config/', include('core.urls')),
    # OpenAPI 文档
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
