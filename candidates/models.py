from django.conf import settings
from django.db import models


class ApplicationStatus(models.TextChoices):
  PENDING = 'pending', '待审核'
  APPROVED = 'approved', '已通过'
  REJECTED = 'rejected', '已驳回'


class Gender(models.TextChoices):
  MALE = 'male', '男'
  FEMALE = 'female', '女'


class RegistrationType(models.TextChoices):
  INDIVIDUAL = 'individual', '个人'
  GROUP = 'group', '团体'


class Candidate(models.Model):
  """候选人/参赛人物（个人或团体）。"""

  name = models.CharField('姓名/团体名称', max_length=100)
  number = models.PositiveIntegerField('编号', unique=True, help_text='参赛编号')
  registration_type = models.CharField(
    '报名类型',
    max_length=20,
    choices=RegistrationType.choices,
    default=RegistrationType.INDIVIDUAL,
  )
  gender = models.CharField(
    '性别',
    max_length=10,
    choices=Gender.choices,
    blank=True,
    null=True,
    help_text='个人报名填写；团体报名可为空',
  )
  age = models.PositiveSmallIntegerField(
    '年龄',
    blank=True,
    null=True,
    help_text='个人报名填写；团体报名可为空',
  )
  introduction = models.TextField('个人介绍', blank=True, default='')
  avatar = models.ImageField('头像', upload_to='candidates/avatars/')
  vote_count = models.PositiveIntegerField('投票数', default=0)
  heat_score = models.PositiveIntegerField('热度值', default=0, help_text='投票+礼物转换的热度')
  is_active = models.BooleanField(
    '是否参赛',
    default=True,
    help_text='取消勾选即下架，前台列表/排行榜不再展示该候选人',
  )
  created_at = models.DateTimeField('创建时间', auto_now_add=True)
  updated_at = models.DateTimeField('更新时间', auto_now=True)

  class Meta:
    verbose_name = '候选人'
    verbose_name_plural = '候选人'
    ordering = ['number']

  def __str__(self):
    return f'{self.number} - {self.name}'


class CandidatePhoto(models.Model):
  """候选人照片。"""

  candidate = models.ForeignKey(
    Candidate,
    on_delete=models.CASCADE,
    related_name='photos',
    verbose_name='候选人',
  )
  image = models.ImageField('照片', upload_to='candidates/photos/')
  caption = models.CharField('说明', max_length=200, blank=True, default='')
  sort_order = models.PositiveIntegerField('排序', default=0)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)

  class Meta:
    verbose_name = '候选人照片'
    verbose_name_plural = '候选人照片'
    ordering = ['sort_order', 'id']

  def __str__(self):
    return f'{self.candidate.name} - 照片{self.id}'


class CandidateMember(models.Model):
  """团体候选人数员。"""

  candidate = models.ForeignKey(
    Candidate,
    on_delete=models.CASCADE,
    related_name='members',
    verbose_name='候选人',
  )
  name = models.CharField('姓名', max_length=100)
  age = models.PositiveSmallIntegerField('年龄')
  sort_order = models.PositiveIntegerField('排序', default=0)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)

  class Meta:
    verbose_name = '团体成员'
    verbose_name_plural = '团体成员'
    ordering = ['sort_order', 'id']

  def __str__(self):
    return f'{self.candidate.name} - {self.name}'


class CandidateApplication(models.Model):
  """用户自主报名申请，后台审核通过后创建候选人。"""

  user = models.OneToOneField(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='candidate_application',
    verbose_name='申请人',
  )
  registration_type = models.CharField(
    '报名类型',
    max_length=20,
    choices=RegistrationType.choices,
    default=RegistrationType.INDIVIDUAL,
  )
  name = models.CharField('姓名/团体名称', max_length=100)
  gender = models.CharField(
    '性别',
    max_length=10,
    choices=Gender.choices,
    blank=True,
    null=True,
    help_text='个人报名填写；团体报名可为空',
  )
  age = models.PositiveSmallIntegerField(
    '年龄',
    blank=True,
    null=True,
    help_text='个人报名填写；团体报名可为空',
  )
  introduction = models.TextField('个人介绍', blank=True, default='')
  avatar = models.ImageField('头像', upload_to='applications/avatars/')
  status = models.CharField(
    '审核状态',
    max_length=20,
    choices=ApplicationStatus.choices,
    default=ApplicationStatus.PENDING,
  )
  reject_reason = models.TextField('驳回原因', blank=True, default='')
  candidate = models.OneToOneField(
    Candidate,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='application',
    verbose_name='关联候选人',
  )
  reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
  reviewed_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='reviewed_applications',
    verbose_name='审核人',
  )
  created_at = models.DateTimeField('提交时间', auto_now_add=True)
  updated_at = models.DateTimeField('更新时间', auto_now=True)

  class Meta:
    verbose_name = '报名申请'
    verbose_name_plural = '报名申请'
    ordering = ['-created_at']

  def __str__(self):
    return f'{self.name} - {self.get_status_display()}'

  @property
  def status_message(self):
    if self.status == ApplicationStatus.PENDING:
      if self.candidate_id:
        return '您的资料修改已提交，正在审核中，请耐心等待'
      return '您的报名申请已提交，正在审核中，请耐心等待'
    messages = {
      ApplicationStatus.APPROVED: '恭喜！您的报名申请已通过审核，您已成为候选人，可在候选人列表中查看',
      ApplicationStatus.REJECTED: '审核未通过，请根据反馈修改资料后重新提交',
    }
    msg = messages.get(self.status, '')
    if self.status == ApplicationStatus.REJECTED and self.reject_reason:
      msg = f'{msg}。驳回原因：{self.reject_reason}'
    return msg


class CandidateApplicationPhoto(models.Model):
  """报名申请附带照片。"""

  application = models.ForeignKey(
    CandidateApplication,
    on_delete=models.CASCADE,
    related_name='photos',
    verbose_name='报名申请',
  )
  image = models.ImageField('照片', upload_to='applications/photos/')
  caption = models.CharField('说明', max_length=200, blank=True, default='')
  sort_order = models.PositiveIntegerField('排序', default=0)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)

  class Meta:
    verbose_name = '报名照片'
    verbose_name_plural = '报名照片'
    ordering = ['sort_order', 'id']

  def __str__(self):
    return f'{self.application.name} - 照片{self.id}'


class CandidateApplicationMember(models.Model):
  """团体报名成员。"""

  application = models.ForeignKey(
    CandidateApplication,
    on_delete=models.CASCADE,
    related_name='members',
    verbose_name='报名申请',
  )
  name = models.CharField('姓名', max_length=100)
  age = models.PositiveSmallIntegerField('年龄')
  sort_order = models.PositiveIntegerField('排序', default=0)
  created_at = models.DateTimeField('创建时间', auto_now_add=True)

  class Meta:
    verbose_name = '报名成员'
    verbose_name_plural = '报名成员'
    ordering = ['sort_order', 'id']

  def __str__(self):
    return f'{self.application.name} - {self.name}'
