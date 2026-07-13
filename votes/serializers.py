from rest_framework import serializers

from votes.models import Vote


class VoteSerializer(serializers.ModelSerializer):
  candidate_name = serializers.CharField(source='candidate.name', read_only=True)
  candidate_number = serializers.IntegerField(source='candidate.number', read_only=True)

  class Meta:
    model = Vote
    fields = ['id', 'candidate', 'candidate_name', 'candidate_number', 'vote_date', 'created_at']
    read_only_fields = fields


class CastVoteSerializer(serializers.Serializer):
  candidate_id = serializers.IntegerField(help_text='候选人 ID')


class VoteStatusSerializer(serializers.Serializer):
  daily_limit = serializers.IntegerField(help_text='每日投票上限')
  today_votes = serializers.IntegerField(help_text='今日已投票数')
  remaining_votes = serializers.IntegerField(help_text='今日剩余票数')
