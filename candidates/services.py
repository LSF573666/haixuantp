from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from candidates.models import (
  ApplicationStatus,
  Candidate,
  CandidateApplication,
  CandidateApplicationPhoto,
  CandidatePhoto,
)


def get_next_candidate_number():
  max_number = Candidate.objects.aggregate(max_num=Max('number'))['max_num']
  return (max_number or 0) + 1


def submit_application(user, validated_data, photos=None):
  """提交或重新提交报名申请。驳回后可修改资料重新提交，头像/照片可选更新。"""
  existing = CandidateApplication.objects.filter(user=user).first()

  if existing and existing.status == ApplicationStatus.PENDING:
    raise ValueError('您已有待审核的报名申请，请耐心等待审核结果')

  if existing and existing.status == ApplicationStatus.APPROVED:
    raise ValueError('您已成为候选人，无需重复报名')

  with transaction.atomic():
    if existing and existing.status == ApplicationStatus.REJECTED:
      application = existing
      application.name = validated_data['name']
      application.introduction = validated_data.get('introduction', '')
      if validated_data.get('avatar'):
        application.avatar = validated_data['avatar']
      application.status = ApplicationStatus.PENDING
      application.reject_reason = ''
      application.reviewed_at = None
      application.reviewed_by = None
      application.save()

      if photos:
        application.photos.all().delete()
        for index, photo in enumerate(photos):
          CandidateApplicationPhoto.objects.create(
            application=application,
            image=photo,
            sort_order=index,
          )
    else:
      if not validated_data.get('avatar'):
        raise ValueError('请上传头像')
      application = CandidateApplication.objects.create(
        user=user,
        name=validated_data['name'],
        introduction=validated_data.get('introduction', ''),
        avatar=validated_data['avatar'],
      )
      for index, photo in enumerate(photos or []):
        CandidateApplicationPhoto.objects.create(
          application=application,
          image=photo,
          sort_order=index,
        )

  return application


def approve_application(application, reviewer):
  """审核通过：创建候选人（默认参赛展示）并关联申请。"""
  if application.status != ApplicationStatus.PENDING:
    raise ValueError('只能审核待审核状态的申请')

  with transaction.atomic():
    candidate = Candidate.objects.create(
      name=application.name,
      number=get_next_candidate_number(),
      introduction=application.introduction,
      avatar=application.avatar,
      is_active=True,
    )

    for photo in application.photos.all():
      CandidatePhoto.objects.create(
        candidate=candidate,
        image=photo.image,
        caption=photo.caption,
        sort_order=photo.sort_order,
      )

    application.status = ApplicationStatus.APPROVED
    application.candidate = candidate
    application.reviewed_at = timezone.now()
    application.reviewed_by = reviewer
    application.reject_reason = ''
    application.save()

  return application


def reject_application(application, reviewer, reason=''):
  """审核驳回。"""
  if application.status != ApplicationStatus.PENDING:
    raise ValueError('只能审核待审核状态的申请')

  application.status = ApplicationStatus.REJECTED
  application.reject_reason = reason
  application.reviewed_at = timezone.now()
  application.reviewed_by = reviewer
  application.save()
  return application
