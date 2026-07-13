from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gifts.models import Gift
from gifts.serializers import GiftSerializer, GiftTransactionSerializer, SendGiftSerializer
from gifts.services import send_gift


class GiftListView(generics.ListAPIView):
  permission_classes = [AllowAny]
  serializer_class = GiftSerializer
  queryset = Gift.objects.filter(is_active=True)

  @extend_schema(tags=['礼物'], summary='获取礼物列表')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)


class SendGiftView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['礼物'],
    summary='赠送礼物',
    description='使用账户余额购买礼物赠送给候选人，礼物热度值将累加到候选人热度。',
    request=SendGiftSerializer,
    responses={201: GiftTransactionSerializer},
  )
  def post(self, request):
    serializer = SendGiftSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
      record = send_gift(
        request.user,
        serializer.validated_data['candidate_id'],
        serializer.validated_data['gift_id'],
        serializer.validated_data.get('quantity', 1),
      )
    except ValueError as e:
      return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
      'message': '礼物赠送成功',
      'transaction': GiftTransactionSerializer(record).data,
      'balance': str(request.user.balance),
    }, status=status.HTTP_201_CREATED)


class GiftHistoryView(generics.ListAPIView):
  permission_classes = [IsAuthenticated]
  serializer_class = GiftTransactionSerializer

  @extend_schema(tags=['礼物'], summary='我的礼物赠送记录')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def get_queryset(self):
    return self.request.user.sent_gifts.select_related('gift', 'candidate').all()
