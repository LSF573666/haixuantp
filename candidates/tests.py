from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from candidates.models import (
  ApplicationStatus,
  Candidate,
  CandidateApplication,
  CandidateApplicationMember,
  CandidateMember,
  Gender,
  RegistrationType,
)
from candidates.serializers import CandidateApplicationSubmitSerializer
from candidates.services import (
  approve_application,
  build_candidate_rank_map,
  reject_application,
  resolve_avatar_object_key,
  submit_application,
)

User = get_user_model()


@override_settings(
  ALIYUN_OSS_BUCKET='aibaobendev',
  OSS_ENDPOINT='oss-cn-hangzhou.aliyuncs.com',
  OSS_BASE_URL='',
  MEDIA_URL='https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/',
)
class ResolveAvatarObjectKeyTests(TestCase):
  def test_full_url(self):
    key = resolve_avatar_object_key(
      'https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/12/avatar.jpg',
      12,
    )
    self.assertEqual(key, 'uploads/12/avatar.jpg')

  def test_reject_other_user_prefix(self):
    with self.assertRaisesMessage(ValueError, '头像 URL 不在允许的上传目录内'):
      resolve_avatar_object_key(
        'https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/99/avatar.jpg',
        12,
      )

  def test_reject_other_bucket(self):
    with self.assertRaisesMessage(ValueError, '头像 URL 不属于当前 OSS 存储'):
      resolve_avatar_object_key(
        'https://other-bucket.oss-cn-hangzhou.aliyuncs.com/uploads/12/avatar.jpg',
        12,
      )

  @override_settings(OSS_BASE_URL='https://toupiao.aibaoben.com')
  def test_accept_cdn_base_url(self):
    key = resolve_avatar_object_key(
      'https://toupiao.aibaoben.com/uploads/12/avatar.jpg',
      12,
    )
    self.assertEqual(key, 'uploads/12/avatar.jpg')


class ApproveApplicationTests(TestCase):
  def setUp(self):
    self.reviewer = User.objects.create_superuser(
      username='admin',
      password='adminpass',
    )
    self.applicant = User.objects.create_user(
      username='user1',
      phone='13800000001',
    )
    self.application = CandidateApplication(
      user=self.applicant,
      registration_type=RegistrationType.INDIVIDUAL,
      name='测试候选人',
      gender=Gender.MALE,
      age=22,
      introduction='介绍',
      status=ApplicationStatus.PENDING,
    )
    self.application.avatar.name = 'applications/avatars/test.jpg'
    self.application.save()

  def test_approve_creates_candidate_and_updates_status(self):
    approve_application(self.application, self.reviewer)
    self.application.refresh_from_db()

    self.assertEqual(self.application.status, ApplicationStatus.APPROVED)
    self.assertIsNotNone(self.application.candidate)
    self.assertEqual(self.application.reviewed_by, self.reviewer)
    self.assertEqual(Candidate.objects.count(), 1)
    self.assertEqual(self.application.candidate.name, '测试候选人')
    self.assertEqual(
      self.application.candidate.registration_type,
      RegistrationType.INDIVIDUAL,
    )


class CandidateApplicationAdminApproveViewTests(TestCase):
  def setUp(self):
    self.reviewer = User.objects.create_superuser(
      username='admin',
      password='adminpass',
    )
    self.client.login(username='admin', password='adminpass')
    self.applicant = User.objects.create_user(
      username='user2',
      phone='13800000002',
    )
    self.application = CandidateApplication(
      user=self.applicant,
      registration_type=RegistrationType.INDIVIDUAL,
      name='待审核用户',
      gender=Gender.FEMALE,
      age=20,
      introduction='介绍',
      status=ApplicationStatus.PENDING,
    )
    self.application.avatar.name = 'applications/avatars/test.jpg'
    self.application.save()

  def test_approve_view_updates_status(self):
    url = reverse(
      'admin:candidates_candidateapplication_approve',
      args=[self.application.pk],
    )
    response = self.client.post(url)
    self.application.refresh_from_db()

    self.assertEqual(response.status_code, 302)
    self.assertEqual(self.application.status, ApplicationStatus.APPROVED)
    self.assertIsNotNone(self.application.candidate)


class SubmitApplicationUpdateTests(TestCase):
  def setUp(self):
    self.reviewer = User.objects.create_superuser(
      username='admin2',
      password='adminpass',
    )
    self.applicant = User.objects.create_user(
      username='user3',
      phone='13800000003',
    )
    self.application = CandidateApplication(
      user=self.applicant,
      registration_type=RegistrationType.INDIVIDUAL,
      name='原名',
      gender=Gender.MALE,
      age=25,
      introduction='原介绍',
      status=ApplicationStatus.PENDING,
    )
    self.application.avatar.name = 'applications/avatars/test.jpg'
    self.application.save()

  def test_approved_user_can_submit_profile_update(self):
    approve_application(self.application, self.reviewer)
    candidate_id = self.application.candidate_id

    updated = submit_application(
      self.applicant,
      {
        'registration_type': RegistrationType.INDIVIDUAL,
        'name': '新名字',
        'gender': Gender.FEMALE,
        'age': 26,
        'introduction': '新介绍',
        'members': [],
      },
    )
    updated.refresh_from_db()

    self.assertEqual(updated.status, ApplicationStatus.PENDING)
    self.assertEqual(updated.name, '新名字')
    self.assertEqual(updated.age, 26)
    self.assertEqual(updated.candidate_id, candidate_id)
    self.assertEqual(Candidate.objects.count(), 1)

  def test_pending_update_blocks_resubmit(self):
    approve_application(self.application, self.reviewer)
    submit_application(
      self.applicant,
      {
        'registration_type': RegistrationType.INDIVIDUAL,
        'name': '新名字',
        'gender': Gender.FEMALE,
        'age': 26,
        'members': [],
      },
    )

    with self.assertRaisesMessage(
      ValueError,
      '您已有待审核的资料修改，请耐心等待审核结果',
    ):
      submit_application(
        self.applicant,
        {
          'registration_type': RegistrationType.INDIVIDUAL,
          'name': '再次修改',
          'gender': Gender.MALE,
          'age': 27,
          'members': [],
        },
      )

  def test_reapprove_updates_existing_candidate(self):
    approve_application(self.application, self.reviewer)
    submit_application(
      self.applicant,
      {
        'registration_type': RegistrationType.INDIVIDUAL,
        'name': '新名字',
        'gender': Gender.FEMALE,
        'age': 26,
        'introduction': '新介绍',
        'members': [],
      },
    )
    self.application.refresh_from_db()

    approve_application(self.application, self.reviewer)
    self.application.candidate.refresh_from_db()

    self.assertEqual(self.application.status, ApplicationStatus.APPROVED)
    self.assertEqual(self.application.candidate.name, '新名字')
    self.assertEqual(self.application.candidate.gender, Gender.FEMALE)
    self.assertEqual(self.application.candidate.age, 26)
    self.assertEqual(self.application.candidate.introduction, '新介绍')
    self.assertEqual(Candidate.objects.count(), 1)

  def test_reject_update_keeps_candidate_with_old_profile(self):
    approve_application(self.application, self.reviewer)
    submit_application(
      self.applicant,
      {
        'registration_type': RegistrationType.INDIVIDUAL,
        'name': '新名字',
        'gender': Gender.FEMALE,
        'age': 26,
        'introduction': '新介绍',
        'members': [],
      },
    )
    self.application.refresh_from_db()

    reject_application(self.application, self.reviewer, '照片不清晰')
    self.application.candidate.refresh_from_db()

    self.assertEqual(self.application.status, ApplicationStatus.REJECTED)
    self.assertEqual(self.application.candidate.name, '原名')
    self.assertEqual(self.application.candidate.gender, Gender.MALE)
    self.assertIsNotNone(self.application.candidate_id)


class GroupApplicationTests(TestCase):
  def setUp(self):
    self.reviewer = User.objects.create_superuser(
      username='admin3',
      password='adminpass',
    )
    self.applicant = User.objects.create_user(
      username='user4',
      phone='13800000004',
    )

  def test_submit_serializer_requires_at_least_three_members(self):
    serializer = CandidateApplicationSubmitSerializer(data={
      'registration_type': RegistrationType.GROUP,
      'name': '青春舞团',
      'members': [
        {'name': '甲', 'age': 20},
        {'name': '乙', 'age': 21},
      ],
      'avatar_url': 'https://aibaobendev.oss-cn-hangzhou.aliyuncs.com/uploads/1/a.jpg',
    })
    self.assertFalse(serializer.is_valid())
    self.assertIn('members', serializer.errors)

  def test_approve_group_creates_candidate_with_members(self):
    application = CandidateApplication(
      user=self.applicant,
      registration_type=RegistrationType.GROUP,
      name='青春舞团',
      introduction='团体介绍',
      status=ApplicationStatus.PENDING,
    )
    application.avatar.name = 'applications/avatars/group.jpg'
    application.save()
    CandidateApplicationMember.objects.create(
      application=application, name='甲', age=20, sort_order=0,
    )
    CandidateApplicationMember.objects.create(
      application=application, name='乙', age=21, sort_order=1,
    )
    CandidateApplicationMember.objects.create(
      application=application, name='丙', age=22, sort_order=2,
    )

    approve_application(application, self.reviewer)
    application.refresh_from_db()

    self.assertEqual(application.status, ApplicationStatus.APPROVED)
    self.assertEqual(application.candidate.registration_type, RegistrationType.GROUP)
    self.assertEqual(application.candidate.name, '青春舞团')
    self.assertIsNone(application.candidate.age)
    members = list(application.candidate.members.order_by('sort_order').values_list('name', 'age'))
    self.assertEqual(members, [('甲', 20), ('乙', 21), ('丙', 22)])
    self.assertEqual(CandidateMember.objects.count(), 3)


class CandidateFilterTests(TestCase):
  def setUp(self):
    Candidate.objects.create(
      name='男选手',
      number=1,
      registration_type=RegistrationType.INDIVIDUAL,
      gender=Gender.MALE,
      age=22,
      avatar='candidates/avatars/male.jpg',
    )
    Candidate.objects.create(
      name='女选手',
      number=2,
      registration_type=RegistrationType.INDIVIDUAL,
      gender=Gender.FEMALE,
      age=20,
      avatar='candidates/avatars/female.jpg',
    )
    group = Candidate.objects.create(
      name='青春舞团',
      number=3,
      registration_type=RegistrationType.GROUP,
      avatar='candidates/avatars/group.jpg',
    )
    CandidateMember.objects.create(candidate=group, name='甲', age=20, sort_order=0)

  def test_list_filter_by_gender(self):
    response = self.client.get('/api/candidates/', {'gender': Gender.FEMALE})
    self.assertEqual(response.status_code, 200)
    results = response.json()['results']
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0]['gender'], Gender.FEMALE)
    self.assertEqual(results[0]['gender_display'], '女')

  def test_invalid_gender_param(self):
    response = self.client.get('/api/candidates/', {'gender': 'unknown'})
    self.assertEqual(response.status_code, 400)

  def test_list_without_registration_type_returns_all(self):
    response = self.client.get('/api/candidates/')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()['count'], 3)

  def test_list_filter_by_registration_type_group(self):
    response = self.client.get('/api/candidates/', {'registration_type': 'group'})
    self.assertEqual(response.status_code, 200)
    results = response.json()['results']
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0]['registration_type'], RegistrationType.GROUP)
    self.assertEqual(results[0]['name'], '青春舞团')
    self.assertEqual(len(results[0]['members']), 1)

  def test_list_filter_by_registration_type_individual(self):
    response = self.client.get('/api/candidates/', {'registration_type': 'individual'})
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()['count'], 2)

  def test_invalid_registration_type_param(self):
    response = self.client.get('/api/candidates/', {'registration_type': 'team'})
    self.assertEqual(response.status_code, 400)

  def test_ranking_filter_by_registration_type(self):
    response = self.client.get('/api/candidates/ranking/', {'registration_type': 'group'})
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual(len(data), 1)
    self.assertEqual(data[0]['registration_type'], RegistrationType.GROUP)

  def test_list_search_by_name(self):
    response = self.client.get('/api/candidates/', {'name': '女'})
    self.assertEqual(response.status_code, 200)
    results = response.json()['results']
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0]['name'], '女选手')

  def test_list_search_by_name_partial_match(self):
    response = self.client.get('/api/candidates/', {'name': '舞团'})
    self.assertEqual(response.status_code, 200)
    results = response.json()['results']
    self.assertEqual(len(results), 1)
    self.assertEqual(results[0]['name'], '青春舞团')

  def test_list_search_by_name_no_match(self):
    response = self.client.get('/api/candidates/', {'name': '不存在'})
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()['count'], 0)

  def test_ranking_search_by_name(self):
    response = self.client.get('/api/candidates/ranking/', {'name': '男选手'})
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual(len(data), 1)
    self.assertEqual(data[0]['name'], '男选手')


class CandidateSortByTests(TestCase):
  def setUp(self):
    # 票数最高但热度不是最高 → 用于区分两种排序
    self.by_votes = Candidate.objects.create(
      name='高票低热',
      number=1,
      registration_type=RegistrationType.INDIVIDUAL,
      gender=Gender.MALE,
      age=22,
      avatar='candidates/avatars/votes.jpg',
      vote_count=100,
      heat_score=50,
    )
    self.by_heat = Candidate.objects.create(
      name='高热低票',
      number=2,
      registration_type=RegistrationType.INDIVIDUAL,
      gender=Gender.FEMALE,
      age=20,
      avatar='candidates/avatars/heat.jpg',
      vote_count=40,
      heat_score=200,
    )
    self.mid = Candidate.objects.create(
      name='中等',
      number=3,
      registration_type=RegistrationType.INDIVIDUAL,
      gender=Gender.MALE,
      age=21,
      avatar='candidates/avatars/mid.jpg',
      vote_count=60,
      heat_score=80,
    )

  def test_list_default_orders_by_number(self):
    response = self.client.get('/api/candidates/')
    self.assertEqual(response.status_code, 200)
    names = [item['name'] for item in response.json()['results']]
    self.assertEqual(names, ['高票低热', '高热低票', '中等'])

  def test_list_sort_by_heat_score(self):
    response = self.client.get('/api/candidates/', {'sort_by': 'heat_score'})
    self.assertEqual(response.status_code, 200)
    names = [item['name'] for item in response.json()['results']]
    self.assertEqual(names, ['高热低票', '中等', '高票低热'])

  def test_list_sort_by_vote_count(self):
    response = self.client.get('/api/candidates/', {'sort_by': 'vote_count'})
    self.assertEqual(response.status_code, 200)
    names = [item['name'] for item in response.json()['results']]
    self.assertEqual(names, ['高票低热', '中等', '高热低票'])

  def test_ranking_default_sort_by_heat(self):
    response = self.client.get('/api/candidates/ranking/')
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual([item['name'] for item in data], ['高热低票', '中等', '高票低热'])
    self.assertEqual([item['rank'] for item in data], [1, 2, 3])

  def test_ranking_sort_by_vote_count(self):
    response = self.client.get('/api/candidates/ranking/', {'sort_by': 'vote_count'})
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual([item['name'] for item in data], ['高票低热', '中等', '高热低票'])
    self.assertEqual(data[0]['rank'], 1)
    self.assertEqual(data[0]['vote_count'], 100)

  def test_invalid_sort_by_param(self):
    response = self.client.get('/api/candidates/', {'sort_by': 'popularity'})
    self.assertEqual(response.status_code, 400)
    response = self.client.get('/api/candidates/ranking/', {'sort_by': 'popularity'})
    self.assertEqual(response.status_code, 400)


class CandidateRankGapTests(TestCase):
  def setUp(self):
    self.first = Candidate.objects.create(
      name='第一名',
      number=1,
      registration_type=RegistrationType.INDIVIDUAL,
      gender=Gender.MALE,
      age=22,
      avatar='candidates/avatars/first.jpg',
      vote_count=100,
      heat_score=120,
    )
    self.second = Candidate.objects.create(
      name='第二名',
      number=2,
      registration_type=RegistrationType.INDIVIDUAL,
      gender=Gender.FEMALE,
      age=20,
      avatar='candidates/avatars/second.jpg',
      vote_count=80,
      heat_score=90,
    )
    self.third = Candidate.objects.create(
      name='第三名',
      number=3,
      registration_type=RegistrationType.INDIVIDUAL,
      gender=Gender.MALE,
      age=21,
      avatar='candidates/avatars/third.jpg',
      vote_count=80,
      heat_score=70,
    )

  def test_build_candidate_rank_map(self):
    rank_map = build_candidate_rank_map()

    self.assertEqual(rank_map[self.first.id]['rank'], 1)
    self.assertIsNone(rank_map[self.first.id]['votes_behind_previous'])
    self.assertEqual(rank_map[self.second.id]['rank'], 2)
    self.assertEqual(rank_map[self.second.id]['votes_behind_previous'], 20)
    self.assertEqual(rank_map[self.third.id]['rank'], 3)
    self.assertEqual(rank_map[self.third.id]['votes_behind_previous'], 0)

  def test_detail_returns_rank_gap(self):
    response = self.client.get(f'/api/candidates/{self.second.id}/')
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual(data['rank'], 2)
    self.assertEqual(data['votes_behind_previous'], 20)

  def test_detail_first_place_hides_gap(self):
    response = self.client.get(f'/api/candidates/{self.first.id}/')
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertEqual(data['rank'], 1)
    self.assertIsNone(data['votes_behind_previous'])

  def test_list_returns_rank_gap(self):
    response = self.client.get('/api/candidates/')
    self.assertEqual(response.status_code, 200)
    results = {item['id']: item for item in response.json()['results']}
    self.assertEqual(results[self.second.id]['votes_behind_previous'], 20)
    self.assertIsNone(results[self.first.id]['votes_behind_previous'])
