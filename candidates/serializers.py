from rest_framework import serializers

from candidates.models import (
  Candidate,
  CandidateApplication,
  CandidateApplicationPhoto,
  CandidatePhoto,
)


class CandidatePhotoSerializer(serializers.ModelSerializer):
  class Meta:
    model = CandidatePhoto
    fields = ['id', 'image', 'caption', 'sort_order']


class CandidateListSerializer(serializers.ModelSerializer):
  class Meta:
    model = Candidate
    fields = [
      'id', 'name', 'number', 'introduction', 'avatar',
      'vote_count', 'heat_score', 'is_active',
    ]


class CandidateDetailSerializer(serializers.ModelSerializer):
  photos = CandidatePhotoSerializer(many=True, read_only=True)

  class Meta:
    model = Candidate
    fields = [
      'id', 'name', 'number', 'introduction', 'avatar',
      'vote_count', 'heat_score', 'is_active', 'photos',
      'created_at', 'updated_at',
    ]


class CandidateRankingSerializer(serializers.ModelSerializer):
  rank = serializers.IntegerField(read_only=True)

  class Meta:
    model = Candidate
    fields = ['rank', 'id', 'name', 'number', 'avatar', 'vote_count', 'heat_score']


class CandidateApplicationPhotoSerializer(serializers.ModelSerializer):
  class Meta:
    model = CandidateApplicationPhoto
    fields = ['id', 'image', 'caption', 'sort_order']


class CandidateApplicationSubmitSerializer(serializers.Serializer):
  name = serializers.CharField(max_length=100)
  introduction = serializers.CharField(required=False, allow_blank=True, default='')
  avatar = serializers.ImageField(required=False, allow_null=True)


class CandidateApplicationSerializer(serializers.ModelSerializer):
  photos = CandidateApplicationPhotoSerializer(many=True, read_only=True)
  status_display = serializers.CharField(source='get_status_display', read_only=True)
  status_message = serializers.CharField(read_only=True)
  candidate_id = serializers.IntegerField(source='candidate.id', read_only=True, allow_null=True)

  class Meta:
    model = CandidateApplication
    fields = [
      'id', 'name', 'introduction', 'avatar', 'photos',
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
