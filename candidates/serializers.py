import json

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from candidates.models import (
  Candidate,
  CandidateApplication,
  CandidateApplicationMember,
  CandidateApplicationPhoto,
  CandidateMember,
  CandidatePhoto,
  Gender,
  RegistrationType,
)

MIN_GROUP_MEMBERS = 3


class CandidateRankMixin(serializers.Serializer):
  rank = serializers.SerializerMethodField()
  votes_behind_previous = serializers.SerializerMethodField(
    help_text='距上一名票数差距；第一名为 null',
  )

  @extend_schema_field(serializers.IntegerField(allow_null=True))
  def get_rank(self, obj):
    info = self._get_rank_map().get(obj.id)
    return info['rank'] if info else None

  @extend_schema_field(serializers.IntegerField(allow_null=True))
  def get_votes_behind_previous(self, obj):
    info = self._get_rank_map().get(obj.id)
    if not info or info['rank'] == 1:
      return None
    return info['votes_behind_previous']

  def _get_rank_map(self):
    rank_map = self.context.get('rank_map')
    if rank_map is None:
      from candidates.services import build_candidate_rank_map

      rank_map = build_candidate_rank_map()
      self.context['rank_map'] = rank_map
    return rank_map


class CandidatePhotoSerializer(serializers.ModelSerializer):
  class Meta:
    model = CandidatePhoto
    fields = ['id', 'image', 'caption', 'sort_order']


class CandidateMemberSerializer(serializers.ModelSerializer):
  class Meta:
    model = CandidateMember
    fields = ['id', 'name', 'age', 'sort_order']


class CandidateListSerializer(CandidateRankMixin, serializers.ModelSerializer):
  gender_display = serializers.CharField(source='get_gender_display', read_only=True)
  registration_type_display = serializers.CharField(
    source='get_registration_type_display',
    read_only=True,
  )
  members = CandidateMemberSerializer(many=True, read_only=True)

  class Meta:
    model = Candidate
    fields = [
      'id', 'name', 'number', 'registration_type', 'registration_type_display',
      'gender', 'gender_display', 'age', 'introduction', 'avatar', 'members',
      'vote_count', 'heat_score', 'rank', 'votes_behind_previous', 'is_active',
    ]


class CandidateDetailSerializer(CandidateRankMixin, serializers.ModelSerializer):
  photos = CandidatePhotoSerializer(many=True, read_only=True)
  members = CandidateMemberSerializer(many=True, read_only=True)
  gender_display = serializers.CharField(source='get_gender_display', read_only=True)
  registration_type_display = serializers.CharField(
    source='get_registration_type_display',
    read_only=True,
  )

  class Meta:
    model = Candidate
    fields = [
      'id', 'name', 'number', 'registration_type', 'registration_type_display',
      'gender', 'gender_display', 'age', 'introduction', 'avatar',
      'vote_count', 'heat_score', 'rank', 'votes_behind_previous',
      'is_active', 'photos', 'members', 'created_at', 'updated_at',
    ]


class CandidateRankingSerializer(serializers.ModelSerializer):
  rank = serializers.IntegerField(read_only=True)
  gender_display = serializers.CharField(source='get_gender_display', read_only=True)
  registration_type_display = serializers.CharField(
    source='get_registration_type_display',
    read_only=True,
  )

  class Meta:
    model = Candidate
    fields = [
      'rank', 'id', 'name', 'number', 'registration_type', 'registration_type_display',
      'gender', 'gender_display', 'age', 'avatar',
      'vote_count', 'heat_score',
    ]


class CandidateApplicationPhotoSerializer(serializers.ModelSerializer):
  class Meta:
    model = CandidateApplicationPhoto
    fields = ['id', 'image', 'caption', 'sort_order']


class CandidateApplicationMemberSerializer(serializers.ModelSerializer):
  class Meta:
    model = CandidateApplicationMember
    fields = ['id', 'name', 'age', 'sort_order']


class ApplicationMemberSubmitSerializer(serializers.Serializer):
  name = serializers.CharField(max_length=100)
  age = serializers.IntegerField(min_value=1, max_value=120)


class CandidateApplicationSubmitSerializer(serializers.Serializer):
  registration_type = serializers.ChoiceField(choices=RegistrationType.choices)
  name = serializers.CharField(max_length=100, help_text='个人姓名或团体名称')
  gender = serializers.ChoiceField(choices=Gender.choices, required=False, allow_null=True)
  age = serializers.IntegerField(min_value=1, max_value=120, required=False, allow_null=True)
  members = ApplicationMemberSubmitSerializer(many=True, required=False, default=list)
  introduction = serializers.CharField(required=False, allow_blank=True, default='')
  avatar = serializers.ImageField(required=False, allow_null=True)
  avatar_url = serializers.CharField(
    required=False,
    allow_blank=True,
    default='',
    help_text='OSS 直传后的头像 URL',
  )
  photos = serializers.ListField(
    child=serializers.CharField(allow_blank=False),
    required=False,
    default=list,
    max_length=9,
    help_text='OSS 直传后的展示照片 URL 列表，最多 9 张',
  )

  def to_internal_value(self, data):
    if hasattr(data, 'copy'):
      data = data.copy()
    # QueryDict 不能直接赋 list/dict，需转为普通 dict
    if hasattr(data, 'lists'):
      data = {key: data.get(key) for key in data.keys()}

    members = data.get('members')
    if isinstance(members, str) and members.strip():
      try:
        data['members'] = json.loads(members)
      except json.JSONDecodeError as exc:
        raise serializers.ValidationError({'members': '成员信息 JSON 格式无效'}) from exc

    photos = data.get('photos')
    if isinstance(photos, str) and photos.strip():
      try:
        data['photos'] = json.loads(photos)
      except json.JSONDecodeError as exc:
        raise serializers.ValidationError({'photos': '照片 URL 列表 JSON 格式无效'}) from exc

    return super().to_internal_value(data)

  def validate(self, attrs):
    avatar = attrs.get('avatar')
    avatar_url = attrs.get('avatar_url', '').strip()
    if avatar and avatar_url:
      raise serializers.ValidationError('avatar 和 avatar_url 不能同时传')
    attrs['avatar_url'] = avatar_url

    registration_type = attrs['registration_type']
    members = attrs.get('members') or []

    if registration_type == RegistrationType.INDIVIDUAL:
      if not attrs.get('gender'):
        raise serializers.ValidationError({'gender': '个人报名须填写性别'})
      if attrs.get('age') is None:
        raise serializers.ValidationError({'age': '个人报名须填写年龄'})
      if members:
        raise serializers.ValidationError({'members': '个人报名无需填写成员'})
      attrs['members'] = []
    else:
      if len(members) < MIN_GROUP_MEMBERS:
        raise serializers.ValidationError({
          'members': f'团体报名至少需要 {MIN_GROUP_MEMBERS} 名成员',
        })
      attrs['gender'] = None
      attrs['age'] = None
      attrs['members'] = members

    return attrs


class CandidateApplicationSerializer(serializers.ModelSerializer):
  photos = CandidateApplicationPhotoSerializer(many=True, read_only=True)
  members = CandidateApplicationMemberSerializer(many=True, read_only=True)
  status_display = serializers.CharField(source='get_status_display', read_only=True)
  status_message = serializers.CharField(read_only=True)
  gender_display = serializers.CharField(source='get_gender_display', read_only=True)
  registration_type_display = serializers.CharField(
    source='get_registration_type_display',
    read_only=True,
  )
  candidate_id = serializers.IntegerField(source='candidate.id', read_only=True, allow_null=True)

  class Meta:
    model = CandidateApplication
    fields = [
      'id', 'registration_type', 'registration_type_display',
      'name', 'gender', 'gender_display', 'age', 'introduction',
      'avatar', 'photos', 'members',
      'status', 'status_display', 'status_message',
      'reject_reason', 'candidate_id',
      'created_at', 'updated_at', 'reviewed_at',
    ]


class CandidateApplicationStatusSerializer(serializers.Serializer):
  has_application = serializers.BooleanField()
  can_apply = serializers.BooleanField()
  can_resubmit = serializers.BooleanField()
  is_candidate = serializers.BooleanField()
  resubmit_hint = serializers.CharField(allow_blank=True)
  application = CandidateApplicationSerializer(allow_null=True)
