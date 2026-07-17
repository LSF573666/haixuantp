from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from votes.serializers import CastVoteSerializer, VoteSerializer, VoteStatusSerializer
from votes.services import cast_vote, get_daily_vote_limit, get_user_remaining_votes, get_user_today_vote_count


class VoteStatusView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(tags=['投票'], summary='查询今日投票状态', responses={200: VoteStatusSerializer})
  def get(self, request):
    data = {
      'daily_limit': get_daily_vote_limit(),
      'today_votes': get_user_today_vote_count(request.user),
      'remaining_votes': get_user_remaining_votes(request.user),
    }
    return Response(VoteStatusSerializer(data).data)


class CastVoteView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['投票'],
    summary='为候选人投票',
    description=(
      '每人每天可投票次数由后台配置（默认3票）。'
      '无论成功或次数用完均返回 HTTP 200，通过 success 字段判断是否投票成功。'
    ),
    request=CastVoteSerializer,
    responses={200: dict},
  )
  def post(self, request):
    serializer = CastVoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    candidate_id = serializer.validated_data['candidate_id']

    try:
      result = cast_vote(request.user, candidate_id)
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    payload = {
      'success': result['success'],
      'message': result['message'],
      'remaining_votes': result['remaining_votes'],
      'daily_limit': result['daily_limit'],
      'today_votes': result['today_votes'],
      'vote': VoteSerializer(result['vote']).data if result['vote'] else None,
    }
    return Response(payload, status=status.HTTP_200_OK)


class VoteHistoryView(generics.ListAPIView):
  permission_classes = [IsAuthenticated]
  serializer_class = VoteSerializer

  @extend_schema(tags=['投票'], summary='我的投票记录')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def get_queryset(self):
    return self.request.user.votes.select_related('candidate').all()
