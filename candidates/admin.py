from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe

from candidates.models import (
  ApplicationStatus,
  Candidate,
  CandidateApplication,
  CandidateApplicationMember,
  CandidateApplicationPhoto,
  CandidateMember,
  CandidatePhoto,
)
from candidates.services import approve_application, reject_application


class CandidatePhotoInline(admin.TabularInline):
  model = CandidatePhoto
  extra = 1
  max_num = 9


class CandidateMemberInline(admin.TabularInline):
  model = CandidateMember
  extra = 0
  fields = ['name', 'age', 'sort_order']


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
  change_form_template = 'admin/candidates/candidate/change_form.html'
  list_display = [
    'number', 'name', 'registration_type', 'gender', 'age', 'vote_count', 'heat_score',
    'active_badge', 'created_at',
  ]
  list_filter = ['is_active', 'registration_type', 'gender', 'created_at']
  search_fields = ['name', 'number']
  inlines = [CandidateMemberInline, CandidatePhotoInline]
  readonly_fields = ['vote_count', 'heat_score', 'created_at', 'updated_at', 'active_badge']
  actions = ['deactivate_candidates', 'activate_candidates']
  list_per_page = 50

  def get_urls(self):
    urls = super().get_urls()
    custom_urls = [
      path(
        '<int:candidate_id>/deactivate/',
        self.admin_site.admin_view(self.deactivate_view),
        name='candidates_candidate_deactivate',
      ),
      path(
        '<int:candidate_id>/activate/',
        self.admin_site.admin_view(self.activate_view),
        name='candidates_candidate_activate',
      ),
    ]
    return custom_urls + urls

  @admin.display(description='上架状态', ordering='is_active')
  def active_badge(self, obj):
    if obj.is_active:
      return mark_safe('<span style="color:#27ae60;font-weight:bold;">展示中</span>')
    return mark_safe('<span style="color:#e74c3c;font-weight:bold;">已下架</span>')

  @admin.action(description='下架选中的候选人（前台不再展示）')
  def deactivate_candidates(self, request, queryset):
    updated = queryset.filter(is_active=True).update(is_active=False)
    self.message_user(request, f'已下架 {updated} 位候选人，前台列表将不再展示')

  @admin.action(description='重新上架选中的候选人')
  def activate_candidates(self, request, queryset):
    updated = queryset.filter(is_active=False).update(is_active=True)
    self.message_user(request, f'已重新上架 {updated} 位候选人')

  def deactivate_view(self, request, candidate_id):
    candidate = Candidate.objects.get(pk=candidate_id)
    if request.method == 'POST':
      if candidate.is_active:
        candidate.is_active = False
        candidate.save(update_fields=['is_active', 'updated_at'])
        self.message_user(
          request,
          f'已下架候选人「{candidate.number} - {candidate.name}」，前台将不再展示',
        )
      else:
        self.message_user(request, '该候选人已处于下架状态', level=messages.WARNING)
      return redirect('admin:candidates_candidate_change', candidate_id)
    return redirect('admin:candidates_candidate_change', candidate_id)

  def activate_view(self, request, candidate_id):
    candidate = Candidate.objects.get(pk=candidate_id)
    if request.method == 'POST':
      if not candidate.is_active:
        candidate.is_active = True
        candidate.save(update_fields=['is_active', 'updated_at'])
        self.message_user(
          request,
          f'已重新上架候选人「{candidate.number} - {candidate.name}」',
        )
      else:
        self.message_user(request, '该候选人已处于展示状态', level=messages.WARNING)
      return redirect('admin:candidates_candidate_change', candidate_id)
    return redirect('admin:candidates_candidate_change', candidate_id)

  def change_view(self, request, object_id, form_url='', extra_context=None):
    extra_context = extra_context or {}
    candidate = Candidate.objects.get(pk=object_id)
    if candidate.is_active:
      extra_context['deactivate_url'] = reverse(
        'admin:candidates_candidate_deactivate',
        args=[object_id],
      )
    else:
      extra_context['activate_url'] = reverse(
        'admin:candidates_candidate_activate',
        args=[object_id],
      )
    return super().change_view(request, object_id, form_url, extra_context)


@admin.register(CandidatePhoto)
class CandidatePhotoAdmin(admin.ModelAdmin):
  list_display = ['candidate', 'caption', 'sort_order', 'created_at']
  list_filter = ['created_at']
  search_fields = ['candidate__name', 'caption']


class CandidateApplicationPhotoInline(admin.TabularInline):
  model = CandidateApplicationPhoto
  extra = 0
  max_num = 9
  readonly_fields = ['image_preview', 'caption', 'sort_order', 'created_at']
  can_delete = False
  fields = ['image_preview', 'caption', 'sort_order', 'created_at']

  @admin.display(description='照片')
  def image_preview(self, obj):
    if obj.image:
      return format_html(
        '<img src="{}" style="max-height:80px;max-width:120px;" />',
        obj.image.url,
      )
    return '-'


class CandidateApplicationMemberInline(admin.TabularInline):
  model = CandidateApplicationMember
  extra = 0
  readonly_fields = ['name', 'age', 'sort_order', 'created_at']
  can_delete = False
  fields = ['name', 'age', 'sort_order', 'created_at']


@admin.register(CandidateApplication)
class CandidateApplicationAdmin(admin.ModelAdmin):
  change_form_template = 'admin/candidates/candidateapplication/change_form.html'
  list_display = [
    'name', 'registration_type', 'gender', 'age', 'user', 'status_badge',
    'created_at', 'reviewed_at', 'candidate_link',
  ]
  list_filter = ['status', 'registration_type', 'gender', 'created_at', 'reviewed_at']
  search_fields = [
    'name', 'user__phone', 'user__nickname',
  ]
  readonly_fields = [
    'user', 'registration_type', 'name', 'gender', 'age', 'introduction',
    'avatar_preview', 'status_badge',
    'candidate', 'reviewed_at', 'reviewed_by',
    'created_at', 'updated_at', 'reject_reason',
  ]
  fields = [
    'user', 'registration_type', 'name', 'gender', 'age', 'introduction', 'avatar_preview',
    'status_badge', 'reject_reason', 'candidate', 'reviewed_at', 'reviewed_by',
    'created_at', 'updated_at',
  ]
  inlines = [CandidateApplicationMemberInline, CandidateApplicationPhotoInline]
  actions = ['approve_applications']

  def get_queryset(self, request):
    return super().get_queryset(request).select_related('user', 'candidate', 'reviewed_by')

  @admin.display(description='头像')
  def avatar_preview(self, obj):
    if obj.avatar:
      return format_html(
        '<img src="{}" style="max-height:120px;max-width:120px;border-radius:8px;" />',
        obj.avatar.url,
      )
    return '-'

  @admin.display(description='审核状态', ordering='status')
  def status_badge(self, obj):
    colors = {
      ApplicationStatus.PENDING: '#e67e22',
      ApplicationStatus.APPROVED: '#27ae60',
      ApplicationStatus.REJECTED: '#e74c3c',
    }
    color = colors.get(obj.status, '#666')
    return format_html(
      '<span style="color:{};font-weight:bold;">{}</span>',
      color,
      obj.get_status_display(),
    )

  def candidate_link(self, obj):
    if obj.candidate:
      url = reverse('admin:candidates_candidate_change', args=[obj.candidate.pk])
      return format_html('<a href="{}">{}</a>', url, obj.candidate)
    return '-'
  candidate_link.short_description = '关联候选人'

  def has_add_permission(self, request):
    return False

  def get_urls(self):
    urls = super().get_urls()
    custom_urls = [
      path(
        '<int:application_id>/approve/',
        self.admin_site.admin_view(self.approve_view),
        name='candidates_candidateapplication_approve',
      ),
      path(
        '<int:application_id>/reject/',
        self.admin_site.admin_view(self.reject_view),
        name='candidates_candidateapplication_reject',
      ),
    ]
    return custom_urls + urls

  @admin.action(description='通过选中的报名申请')
  def approve_applications(self, request, queryset):
    success_count = 0
    for application in queryset.filter(status=ApplicationStatus.PENDING):
      try:
        approve_application(application, request.user)
        success_count += 1
      except ValueError as exc:
        self.message_user(
          request,
          f'申请「{application.name}」审核失败：{exc}',
          level=messages.ERROR,
        )
    if success_count:
      self.message_user(
        request,
        f'已成功通过 {success_count} 条报名申请，候选人已加入候选人列表',
      )

  def approve_view(self, request, application_id):
    application = CandidateApplication.objects.get(pk=application_id)
    if request.method == 'POST':
      try:
        approve_application(application, request.user)
        self.message_user(
          request,
          f'已通过申请「{application.name}」，候选人编号 {application.candidate.number}，'
          f'已展示在候选人列表中',
        )
      except ValueError as exc:
        self.message_user(request, str(exc), level=messages.ERROR)
      return redirect('admin:candidates_candidateapplication_change', application_id)
    return redirect('admin:candidates_candidateapplication_change', application_id)

  def reject_view(self, request, application_id):
    application = CandidateApplication.objects.get(pk=application_id)
    if request.method == 'POST':
      reason = request.POST.get('reject_reason', '').strip()
      try:
        reject_application(application, request.user, reason)
        self.message_user(
          request,
          f'已驳回申请「{application.name}」，用户可修改资料后重新提交',
        )
      except ValueError as exc:
        self.message_user(request, str(exc), level=messages.ERROR)
      return redirect('admin:candidates_candidateapplication_changelist')

    from django.template.response import TemplateResponse
    context = {
      **self.admin_site.each_context(request),
      'application': application,
      'title': f'驳回报名申请 - {application.name}',
    }
    return TemplateResponse(
      request,
      'admin/candidates/candidateapplication/reject_form.html',
      context,
    )

  def change_view(self, request, object_id, form_url='', extra_context=None):
    extra_context = extra_context or {}
    application = CandidateApplication.objects.select_related('user').get(pk=object_id)
    if application.status == ApplicationStatus.PENDING:
      extra_context['approve_url'] = reverse(
        'admin:candidates_candidateapplication_approve',
        args=[object_id],
      )
      extra_context['reject_url'] = reverse(
        'admin:candidates_candidateapplication_reject',
        args=[object_id],
      )
    return super().change_view(request, object_id, form_url, extra_context)
