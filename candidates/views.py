from django.db.models import F
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from candidates.models import ApplicationStatus, Candidate, CandidateApplication
from candidates.serializers import (
  CandidateApplicationSerializer,
  CandidateApplicationStatusSerializer,
  CandidateApplicationSubmitSerializer,
  CandidateDetailSerializer,
  CandidateListSerializer,
  CandidateRankingSerializer,
)
from candidates.services import submit_application


class CandidateListView(generics.ListAPIView):
  permission_classes = [AllowAny]
  serializer_class = CandidateListSerializer
  queryset = Candidate.objects.filter(is_active=True)

  @extend_schema(tags=['候选人'], summary='获取候选人列表')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)


class CandidateDetailView(generics.RetrieveAPIView):
  permission_classes = [AllowAny]
  serializer_class = CandidateDetailSerializer
  queryset = Candidate.objects.filter(is_active=True)

  @extend_schema(tags=['候选人'], summary='获取候选人详情（含照片）')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)


class CandidateRankingView(APIView):
  permission_classes = [AllowAny]

  @extend_schema(
    tags=['候选人'],
    summary='候选人排行榜',
    description='按热度值降序排列的排行榜。',
    responses={200: CandidateRankingSerializer(many=True)},
  )
  def get(self, request):
    candidates = Candidate.objects.filter(is_active=True).order_by(
      '-heat_score', '-vote_count', 'number'
    )
    data = []
    for rank, candidate in enumerate(candidates, start=1):
      item = CandidateRankingSerializer(candidate).data
      item['rank'] = rank
      data.append(item)
    return Response(data)


class CandidateApplicationSubmitView(APIView):
  permission_classes = [IsAuthenticated]
  parser_classes = [MultiPartParser, FormParser]

  @extend_schema(
    tags=['报名'],
    summary='提交报名申请',
    description=(
      '用户上传个人信息报名参加海选，提交后进入待审核状态。'
      '被驳回后可修改姓名、介绍后重新提交；头像和照片可不传，将保留上次内容。'
      '审核通过后自动创建候选人，展示在候选人列表中。'
    ),
    request={
      'multipart/form-data': {
        'type': 'object',
        'properties': {
          'name': {'type': 'string', 'description': '姓名'},
          'introduction': {'type': 'string', 'description': '个人介绍'},
          'avatar': {'type': 'string', 'format': 'binary', 'description': '头像'},
          'photos': {
            'type': 'array',
            'items': {'type': 'string', 'format': 'binary'},
            'description': '展示照片（可多张）',
          },
        },
        'required': ['name'],
      }
    },
    responses={201: CandidateApplicationSerializer},
  )
  def post(self, request):
    serializer = CandidateApplicationSubmitSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    photos = request.FILES.getlist('photos')
    try:
      application = submit_application(
        user=request.user,
        validated_data=serializer.validated_data,
        photos=photos,
      )
    except ValueError as exc:
      return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
      CandidateApplicationSerializer(application).data,
      status=status.HTTP_201_CREATED,
    )


class CandidateApplicationStatusView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    tags=['报名'],
    summary='查询我的报名进度',
    description='返回当前用户的报名状态与进度反馈，供前端展示审核进度。',
    responses={200: CandidateApplicationStatusSerializer},
  )
  def get(self, request):
    application = CandidateApplication.objects.filter(user=request.user).first()

    can_apply = (
      not application or application.status == ApplicationStatus.REJECTED
    )
    can_resubmit = bool(
      application and application.status == ApplicationStatus.REJECTED
    )
    is_candidate = bool(
      application and application.status == ApplicationStatus.APPROVED
    )
    resubmit_hint = (
      '资料被驳回，请修改姓名、介绍或照片后重新提交'
      if can_resubmit else ''
    )

    return Response({
      'has_application': application is not None,
      'can_apply': can_apply,
      'can_resubmit': can_resubmit,
      'is_candidate': is_candidate,
      'resubmit_hint': resubmit_hint,
      'application': (
        CandidateApplicationSerializer(application).data
        if application else None
      ),
    })
