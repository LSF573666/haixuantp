import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from candidates.models import (
  ApplicationStatus,
  Candidate,
  CandidateApplication,
  Gender,
  RegistrationType,
)
from candidates.serializers import (
  CandidateApplicationSerializer,
  CandidateApplicationStatusSerializer,
  CandidateApplicationSubmitSerializer,
  CandidateDetailSerializer,
  CandidateListSerializer,
  CandidateRankingSerializer,
)
from candidates.services import build_candidate_rank_map, submit_application

logger = logging.getLogger(__name__)

MEMBER_SCHEMA = {
  'type': 'array',
  'items': {
    'type': 'object',
    'properties': {
      'name': {'type': 'string', 'description': '成员姓名'},
      'age': {'type': 'integer', 'minimum': 1, 'maximum': 120, 'description': '成员年龄'},
    },
    'required': ['name', 'age'],
  },
  'description': '团体成员列表，至少 3 人；multipart 时可传 JSON 字符串',
}


def validate_gender_param(gender):
  if gender and gender not in Gender.values:
    raise ValueError('性别参数无效，可选值：male、female')


def filter_candidates_by_gender(queryset, gender):
  if not gender:
    return queryset
  return queryset.filter(gender=gender)


def validate_registration_type_param(registration_type):
  if registration_type and registration_type not in RegistrationType.values:
    raise ValueError('报名类型参数无效，可选值：individual、group')


def filter_candidates_by_registration_type(queryset, registration_type):
  if not registration_type:
    return queryset
  return queryset.filter(registration_type=registration_type)


SORT_BY_HEAT = 'heat_score'
SORT_BY_VOTES = 'vote_count'
SORT_BY_CHOICES = (SORT_BY_HEAT, SORT_BY_VOTES)
CANDIDATE_ORDERING = {
  SORT_BY_HEAT: ('-heat_score', '-vote_count', 'number'),
  SORT_BY_VOTES: ('-vote_count', '-heat_score', 'number'),
}


def filter_candidates_by_name(queryset, name):
  if not name:
    return queryset
  return queryset.filter(name__icontains=name)


def apply_candidate_filters(queryset, request):
  gender = request.query_params.get('gender', '').strip()
  registration_type = request.query_params.get('registration_type', '').strip()
  name = request.query_params.get('name', '').strip()
  validate_gender_param(gender)
  validate_registration_type_param(registration_type)
  queryset = filter_candidates_by_gender(queryset, gender)
  queryset = filter_candidates_by_registration_type(queryset, registration_type)
  return filter_candidates_by_name(queryset, name)


def validate_sort_by_param(sort_by):
  if sort_by and sort_by not in SORT_BY_CHOICES:
    raise ValueError('排序参数无效，可选值：heat_score、vote_count')


def apply_candidate_ordering(queryset, request, *, default=None):
  """
  按 sort_by 排序。default 为 None 时保持模型默认（编号升序）；
  排行榜传入 heat_score 作为默认。
  """
  sort_by = request.query_params.get('sort_by', '').strip()
  validate_sort_by_param(sort_by)
  key = sort_by or default
  if not key:
    return queryset
  return queryset.order_by(*CANDIDATE_ORDERING[key])


CANDIDATE_FILTER_PARAMETERS = [
  OpenApiParameter(
    name='gender',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    required=False,
    enum=list(Gender.values),
    description='按性别筛选：male=男，female=女',
  ),
  OpenApiParameter(
    name='registration_type',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    required=False,
    enum=list(RegistrationType.values),
    description='按报名类型筛选：individual=个人，group=团体；不传则返回全部',
  ),
  OpenApiParameter(
    name='name',
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    required=False,
    description='按选手名称模糊搜索（个人姓名或团体名称，不区分大小写）',
  ),
]

CANDIDATE_SORT_PARAMETER = OpenApiParameter(
  name='sort_by',
  type=OpenApiTypes.STR,
  location=OpenApiParameter.QUERY,
  required=False,
  enum=list(SORT_BY_CHOICES),
  description=(
    '排序方式：heat_score=按热度值降序，vote_count=按投票数降序；'
    '列表不传则按编号升序，排行榜不传则默认按热度值'
  ),
)


class CandidateListView(generics.ListAPIView):
  permission_classes = [AllowAny]
  serializer_class = CandidateListSerializer
  queryset = Candidate.objects.filter(is_active=True).prefetch_related('members')

  @extend_schema(
    tags=['候选人'],
    summary='获取候选人列表',
    description=(
      '支持按性别、报名类型筛选，以及按选手名称模糊搜索；'
      '可通过 sort_by 按热度值或投票数降序排列。'
      '不传 sort_by 时按参赛编号升序。'
    ),
    parameters=[*CANDIDATE_FILTER_PARAMETERS, CANDIDATE_SORT_PARAMETER],
  )
  def get(self, request, *args, **kwargs):
    try:
      validate_gender_param(request.query_params.get('gender', '').strip())
      validate_registration_type_param(
        request.query_params.get('registration_type', '').strip(),
      )
      validate_sort_by_param(request.query_params.get('sort_by', '').strip())
    except ValueError as exc:
      return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return super().get(request, *args, **kwargs)

  def get_queryset(self):
    queryset = apply_candidate_filters(super().get_queryset(), self.request)
    return apply_candidate_ordering(queryset, self.request)

  def get_serializer_context(self):
    context = super().get_serializer_context()
    context['rank_map'] = build_candidate_rank_map()
    return context


class CandidateDetailView(generics.RetrieveAPIView):
  permission_classes = [AllowAny]
  serializer_class = CandidateDetailSerializer
  queryset = Candidate.objects.filter(is_active=True).prefetch_related('photos', 'members')

  @extend_schema(tags=['候选人'], summary='获取候选人详情（含照片）')
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def get_serializer_context(self):
    context = super().get_serializer_context()
    context['rank_map'] = build_candidate_rank_map()
    return context


class CandidateRankingView(APIView):
  permission_classes = [AllowAny]

  @extend_schema(
    tags=['候选人'],
    summary='候选人排行榜',
    description=(
      '排行榜，默认按热度值降序；可通过 sort_by=vote_count 改为按投票数降序。'
      '支持 gender、registration_type、name 筛选；不传 registration_type 时返回全部。'
    ),
    parameters=[*CANDIDATE_FILTER_PARAMETERS, CANDIDATE_SORT_PARAMETER],
    responses={200: CandidateRankingSerializer(many=True)},
  )
  def get(self, request):
    queryset = Candidate.objects.filter(is_active=True)
    try:
      queryset = apply_candidate_filters(queryset, request)
      candidates = apply_candidate_ordering(
        queryset, request, default=SORT_BY_HEAT,
      )
    except ValueError as exc:
      return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    data = []
    for rank, candidate in enumerate(candidates, start=1):
      item = CandidateRankingSerializer(candidate).data
      item['rank'] = rank
      data.append(item)
    return Response(data)


class CandidateApplicationSubmitView(APIView):
  permission_classes = [IsAuthenticated]
  parser_classes = [MultiPartParser, FormParser, JSONParser]

  @extend_schema(
    tags=['报名'],
    summary='提交报名申请',
    description=(
      '支持个人报名（individual）与团体报名（group）。'
      '个人报名须填写姓名、性别、年龄；团体报名须填写团体名称，以及至少 3 名成员的姓名和年龄。'
      '头像可通过 `avatar` 文件上传，或通过 `avatar_url` 传 OSS 直传后的 URL。'
      '展示照片通过 `photos` 传 OSS 直传后的 URL 列表（最多 9 张）。'
      '被驳回后可修改资料后重新提交；已成为候选人也可随时修改资料，每次修改均需后台重新审核。'
      '头像和照片可不传，将保留上次内容。审核通过后自动创建或更新候选人。'
    ),
    request={
      'multipart/form-data': {
        'type': 'object',
        'properties': {
          'registration_type': {
            'type': 'string',
            'enum': list(RegistrationType.values),
            'description': '报名类型：individual=个人，group=团体',
          },
          'name': {'type': 'string', 'description': '个人姓名或团体名称'},
          'gender': {
            'type': 'string',
            'enum': list(Gender.values),
            'description': '性别（个人报名必填）',
          },
          'age': {
            'type': 'integer',
            'minimum': 1,
            'maximum': 120,
            'description': '年龄（个人报名必填）',
          },
          'members': MEMBER_SCHEMA,
          'introduction': {'type': 'string', 'description': '个人/团体介绍'},
          'avatar': {
            'type': 'string',
            'format': 'binary',
            'description': '头像文件（与 avatar_url 二选一）',
          },
          'avatar_url': {'type': 'string', 'description': 'OSS 直传后的头像 URL'},
          'photos': {
            'type': 'array',
            'items': {'type': 'string'},
            'maxItems': 9,
            'description': 'OSS 直传后的展示照片 URL 列表；multipart 时可传 JSON 字符串',
          },
        },
        'required': ['registration_type', 'name'],
      },
      'application/json': {
        'type': 'object',
        'properties': {
          'registration_type': {
            'type': 'string',
            'enum': list(RegistrationType.values),
            'description': '报名类型：individual=个人，group=团体',
          },
          'name': {'type': 'string', 'description': '个人姓名或团体名称'},
          'gender': {
            'type': 'string',
            'enum': list(Gender.values),
            'description': '性别（个人报名必填）',
          },
          'age': {
            'type': 'integer',
            'minimum': 1,
            'maximum': 120,
            'description': '年龄（个人报名必填）',
          },
          'members': MEMBER_SCHEMA,
          'introduction': {'type': 'string', 'description': '个人/团体介绍'},
          'avatar_url': {'type': 'string', 'description': 'OSS 直传后的头像 URL'},
          'photos': {
            'type': 'array',
            'items': {'type': 'string'},
            'maxItems': 9,
            'description': 'OSS 直传后的展示照片 URL 列表，最多 9 张',
          },
        },
        'required': ['registration_type', 'name', 'avatar_url'],
      },
    },
    responses={201: CandidateApplicationSerializer},
  )
  def post(self, request):
    serializer = CandidateApplicationSubmitSerializer(data=request.data)
    if not serializer.is_valid():
      logger.warning(
        '报名提交校验失败 user=%s errors=%s fields=%s files=%s',
        request.user.id,
        serializer.errors,
        dict(request.POST),
        list(request.FILES.keys()),
      )
      serializer.is_valid(raise_exception=True)

    try:
      application = submit_application(
        user=request.user,
        validated_data=serializer.validated_data,
      )
    except ValueError as exc:
      logger.warning(
        '报名提交业务失败 user=%s detail=%s fields=%s files=%s',
        request.user.id,
        exc,
        dict(request.POST),
        list(request.FILES.keys()),
      )
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
    application = (
      CandidateApplication.objects
      .filter(user=request.user)
      .prefetch_related('photos', 'members')
      .first()
    )

    can_apply = (
      not application
      or application.status in (
        ApplicationStatus.REJECTED,
        ApplicationStatus.APPROVED,
      )
    )
    can_resubmit = bool(
      application and application.status in (
        ApplicationStatus.REJECTED,
        ApplicationStatus.APPROVED,
      )
    )
    is_candidate = bool(application and application.candidate_id)
    if application and application.status == ApplicationStatus.REJECTED:
      if application.registration_type == RegistrationType.GROUP:
        resubmit_hint = '资料被驳回，请修改团体名称、成员信息、介绍或照片后重新提交'
      else:
        resubmit_hint = '资料被驳回，请修改姓名、性别、年龄、介绍或照片后重新提交'
    elif application and application.status == ApplicationStatus.APPROVED:
      if application.registration_type == RegistrationType.GROUP:
        resubmit_hint = '可修改团体名称、成员信息、介绍、头像或照片，提交后需后台重新审核'
      else:
        resubmit_hint = '可修改姓名、性别、年龄、介绍、头像或照片，提交后需后台重新审核'
    else:
      resubmit_hint = ''

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
