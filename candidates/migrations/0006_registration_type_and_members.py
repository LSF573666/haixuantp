from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

  dependencies = [
    ('candidates', '0005_candidate_age'),
  ]

  operations = [
    migrations.AddField(
      model_name='candidate',
      name='registration_type',
      field=models.CharField(
        choices=[('individual', '个人'), ('group', '团体')],
        default='individual',
        max_length=20,
        verbose_name='报名类型',
      ),
    ),
    migrations.AddField(
      model_name='candidateapplication',
      name='registration_type',
      field=models.CharField(
        choices=[('individual', '个人'), ('group', '团体')],
        default='individual',
        max_length=20,
        verbose_name='报名类型',
      ),
    ),
    migrations.AlterField(
      model_name='candidate',
      name='name',
      field=models.CharField(max_length=100, verbose_name='姓名/团体名称'),
    ),
    migrations.AlterField(
      model_name='candidateapplication',
      name='name',
      field=models.CharField(max_length=100, verbose_name='姓名/团体名称'),
    ),
    migrations.AlterField(
      model_name='candidate',
      name='gender',
      field=models.CharField(
        blank=True,
        choices=[('male', '男'), ('female', '女')],
        help_text='个人报名填写；团体报名可为空',
        max_length=10,
        null=True,
        verbose_name='性别',
      ),
    ),
    migrations.AlterField(
      model_name='candidateapplication',
      name='gender',
      field=models.CharField(
        blank=True,
        choices=[('male', '男'), ('female', '女')],
        help_text='个人报名填写；团体报名可为空',
        max_length=10,
        null=True,
        verbose_name='性别',
      ),
    ),
    migrations.AlterField(
      model_name='candidate',
      name='age',
      field=models.PositiveSmallIntegerField(
        blank=True,
        help_text='个人报名填写；团体报名可为空',
        null=True,
        verbose_name='年龄',
      ),
    ),
    migrations.AlterField(
      model_name='candidateapplication',
      name='age',
      field=models.PositiveSmallIntegerField(
        blank=True,
        help_text='个人报名填写；团体报名可为空',
        null=True,
        verbose_name='年龄',
      ),
    ),
    migrations.CreateModel(
      name='CandidateMember',
      fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('name', models.CharField(max_length=100, verbose_name='姓名')),
        ('age', models.PositiveSmallIntegerField(verbose_name='年龄')),
        ('sort_order', models.PositiveIntegerField(default=0, verbose_name='排序')),
        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
        (
          'candidate',
          models.ForeignKey(
            on_delete=django.db.models.deletion.CASCADE,
            related_name='members',
            to='candidates.candidate',
            verbose_name='候选人',
          ),
        ),
      ],
      options={
        'verbose_name': '团体成员',
        'verbose_name_plural': '团体成员',
        'ordering': ['sort_order', 'id'],
      },
    ),
    migrations.CreateModel(
      name='CandidateApplicationMember',
      fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('name', models.CharField(max_length=100, verbose_name='姓名')),
        ('age', models.PositiveSmallIntegerField(verbose_name='年龄')),
        ('sort_order', models.PositiveIntegerField(default=0, verbose_name='排序')),
        ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
        (
          'application',
          models.ForeignKey(
            on_delete=django.db.models.deletion.CASCADE,
            related_name='members',
            to='candidates.candidateapplication',
            verbose_name='报名申请',
          ),
        ),
      ],
      options={
        'verbose_name': '报名成员',
        'verbose_name_plural': '报名成员',
        'ordering': ['sort_order', 'id'],
      },
    ),
  ]
