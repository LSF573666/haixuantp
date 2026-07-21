from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from candidates.models import (
  ApplicationStatus,
  Candidate,
  CandidateApplication,
  CandidateApplicationMember,
  CandidateApplicationPhoto,
  CandidateMember,
  CandidatePhoto,
  RegistrationType,
)


def get_next_candidate_number():
  max_number = Candidate.objects.aggregate(max_num=Max('number'))['max_num']
  return (max_number or 0) + 1


def build_candidate_rank_map(queryset=None):
  """
  按热度排行榜规则计算每位候选人的名次与距上一名票数差距。
  排序规则与排行榜一致：heat_score 降序，vote_count 降序，number 升序。
  """
  qs = queryset if queryset is not None else Candidate.objects.filter(is_active=True)
  ordered = list(
    qs.order_by('-heat_score', '-vote_count', 'number').values('id', 'vote_count'),
  )
  rank_map = {}
  for rank, item in enumerate(ordered, start=1):
    if rank == 1:
      rank_map[item['id']] = {'rank': 1, 'votes_behind_previous': None}
      continue
    previous = ordered[rank - 2]
    rank_map[item['id']] = {
      'rank': rank,
      'votes_behind_previous': max(0, previous['vote_count'] - item['vote_count']),
    }
  return rank_map


def resolve_oss_object_key(file_url: str, user_id: int, label: str = '文件') -> str:
  """校验 OSS URL，并返回可写入 ImageField 的对象 Key。"""
  url = file_url.strip()
  if not url:
    raise ValueError(f'{label} URL 不能为空')

  bucket = settings.ALIYUN_OSS_BUCKET
  endpoint = settings.OSS_ENDPOINT
  base_url = (settings.OSS_BASE_URL or f'https://{bucket}.{endpoint}').rstrip('/')
  allowed_hosts = {
    urlparse(base_url).netloc,
    f'{bucket}.{endpoint}',
  }

  parsed = urlparse(url)
  if parsed.netloc:
    if parsed.netloc not in allowed_hosts:
      raise ValueError(f'{label} URL 不属于当前 OSS 存储')
    object_key = parsed.path.lstrip('/')
  else:
    object_key = url.lstrip('/')

  required_prefix = f'uploads/{user_id}/'
  if not object_key.startswith(required_prefix):
    raise ValueError(f'{label} URL 不在允许的上传目录内')

  return object_key


def resolve_avatar_object_key(avatar_url: str, user_id: int) -> str:
  """校验 OSS 头像 URL，并返回可写入 ImageField 的对象 Key。"""
  return resolve_oss_object_key(avatar_url, user_id, label='头像')


def _resolve_avatar(validated_data, user_id):
  avatar_file = validated_data.get('avatar')
  avatar_url = validated_data.get('avatar_url', '').strip()
  if avatar_file:
    return avatar_file, None
  if avatar_url:
    return None, resolve_avatar_object_key(avatar_url, user_id)
  return None, None


def _apply_avatar(application, avatar_file=None, avatar_object_key=None):
  if avatar_file:
    application.avatar = avatar_file
  elif avatar_object_key:
    application.avatar.name = avatar_object_key


def _replace_application_photos(application, photo_object_keys):
  application.photos.all().delete()
  for index, object_key in enumerate(photo_object_keys):
    photo = CandidateApplicationPhoto(
      application=application,
      sort_order=index,
    )
    photo.image.name = object_key
    photo.save()


def _replace_application_members(application, members):
  application.members.all().delete()
  for index, member in enumerate(members or []):
    CandidateApplicationMember.objects.create(
      application=application,
      name=member['name'],
      age=member['age'],
      sort_order=index,
    )


def _sync_candidate_members(candidate, application):
  candidate.members.all().delete()
  for member in application.members.all():
    CandidateMember.objects.create(
      candidate=candidate,
      name=member.name,
      age=member.age,
      sort_order=member.sort_order,
    )


MAX_APPLICATION_PHOTOS = 9


def submit_application(user, validated_data, photos=None):
  """提交报名或修改个人资料。驳回后、已成为候选人后均可重新提交，每次提交均需后台审核。"""
  photo_urls = list(photos if photos is not None else validated_data.get('photos') or [])
  if len(photo_urls) > MAX_APPLICATION_PHOTOS:
    raise ValueError(f'展示照片最多上传 {MAX_APPLICATION_PHOTOS} 张')
  photo_object_keys = [
    resolve_oss_object_key(url, user.id, label='照片')
    for url in photo_urls
  ]

  existing = CandidateApplication.objects.filter(user=user).first()

  if existing and existing.status == ApplicationStatus.PENDING:
    raise ValueError('您已有待审核的资料修改，请耐心等待审核结果')

  avatar_file, avatar_object_key = _resolve_avatar(validated_data, user.id)
  members = validated_data.get('members') or []
  registration_type = validated_data['registration_type']

  with transaction.atomic():
    if existing and existing.status in (
      ApplicationStatus.REJECTED,
      ApplicationStatus.APPROVED,
    ):
      application = existing
      application.registration_type = registration_type
      application.name = validated_data['name']
      application.gender = validated_data.get('gender')
      application.age = validated_data.get('age')
      application.introduction = validated_data.get('introduction', '')
      if avatar_file or avatar_object_key:
        _apply_avatar(application, avatar_file, avatar_object_key)
      application.status = ApplicationStatus.PENDING
      application.reject_reason = ''
      application.reviewed_at = None
      application.reviewed_by = None
      application.save()

      if registration_type == RegistrationType.GROUP or members:
        _replace_application_members(application, members)
      elif registration_type == RegistrationType.INDIVIDUAL:
        application.members.all().delete()

      if photo_object_keys:
        _replace_application_photos(application, photo_object_keys)
    else:
      if not avatar_file and not avatar_object_key:
        raise ValueError('请上传头像')
      application = CandidateApplication(
        user=user,
        registration_type=registration_type,
        name=validated_data['name'],
        gender=validated_data.get('gender'),
        age=validated_data.get('age'),
        introduction=validated_data.get('introduction', ''),
      )
      _apply_avatar(application, avatar_file, avatar_object_key)
      application.save()
      _replace_application_members(application, members)
      if photo_object_keys:
        _replace_application_photos(application, photo_object_keys)

  return application


def _sync_candidate_from_application(candidate, application):
  candidate.name = application.name
  candidate.registration_type = application.registration_type
  candidate.gender = application.gender
  candidate.age = application.age
  candidate.introduction = application.introduction
  candidate.avatar = application.avatar
  candidate.save()

  candidate.photos.all().delete()
  for photo in application.photos.all():
    CandidatePhoto.objects.create(
      candidate=candidate,
      image=photo.image,
      caption=photo.caption,
      sort_order=photo.sort_order,
    )
  _sync_candidate_members(candidate, application)


def approve_application(application, reviewer):
  """审核通过：首次通过时创建候选人，资料修改通过时更新已有候选人。"""
  if application.status != ApplicationStatus.PENDING:
    raise ValueError('只能审核待审核状态的申请')

  with transaction.atomic():
    if application.candidate_id:
      _sync_candidate_from_application(application.candidate, application)
      candidate = application.candidate
    else:
      candidate = Candidate.objects.create(
        name=application.name,
        number=get_next_candidate_number(),
        registration_type=application.registration_type,
        gender=application.gender,
        age=application.age,
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
      _sync_candidate_members(candidate, application)
      application.candidate = candidate

    application.status = ApplicationStatus.APPROVED
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
