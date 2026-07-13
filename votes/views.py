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
    description='每人每天可投票次数由后台配置（默认3票）。',
    request=CastVoteSerializer,
    responses={201: dict},
  )
  def post(self, request):
    serializer = CastVoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    candidate_id = serializer.validated_data['candidate_id']

    try:
      vote, remaining = cast_vote(request.user, candidate_id)
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
      'message': '投票成功',
      'vote': VoteSerializer(vote).data,
      'remaining_votes': remaining,
    }, status=status.HTTP_201_CREATED)


class VoteHistoryView(generics.ListAPIView):
  permission_classes = [IsAuthenticated]
  serializer_class = VoteSerializer

  @extend_schema(tags=['投票'], summary='我的投票记录')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def get_queryset(self):
    return self.request.user.votes.select_related('candidate').all()
