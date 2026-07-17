from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import logging

from core.aliyun_sts import assume_oss_upload_role
from core.serializers import OSSStsCredentialSerializer, PublicConfigSerializer
from votes.services import get_daily_vote_limit

logger = logging.getLogger(__name__)


class PublicConfigView(APIView):
  permission_classes = [AllowAny]

  @extend_schema(
    tags=['配置'],
    summary='获取公开配置',
    description='返回前端需要的公开配置项，如今日投票上限等。',
    responses={200: PublicConfigSerializer},
  )
  def get(self, request):
    data = {'daily_vote_limit': get_daily_vote_limit()}
    return Response(PublicConfigSerializer(data).data)


class OSSStsCredentialView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['配置'],
    summary='获取 OSS 上传 STS 临时凭证',
    description=(
      '前端直传 OSS 前调用此接口获取 STS 临时凭证。'
      '凭证仅允许向当前用户目录 `uploads/{user_id}/` 上传文件。'
    ),
    responses={200: OSSStsCredentialSerializer},
  )
  def get(self, request):
    try:
      credentials = assume_oss_upload_role(request.user.id)
    except RuntimeError as exc:
      logger.warning('OSS STS credential request failed: %s', exc)
      return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception:
      logger.exception('Unexpected OSS STS credential error for user %s', request.user.id)
      detail = '获取 STS 凭证失败'
      if settings.DEBUG:
        detail = '获取 STS 凭证失败，请查看服务端日志'
      return Response({'detail': detail}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(credentials)
