from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers import PublicConfigSerializer
from votes.services import get_daily_vote_limit


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
