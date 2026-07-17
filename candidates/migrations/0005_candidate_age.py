from django.db import migrations, models


class Migration(migrations.Migration):

  dependencies = [
    ('candidates', '0004_alter_candidate_is_active'),
  ]

  operations = [
    migrations.AddField(
      model_name='candidate',
      name='age',
      field=models.PositiveSmallIntegerField(default=18, verbose_name='年龄'),
      preserve_default=False,
    ),
    migrations.AddField(
      model_name='candidateapplication',
      name='age',
      field=models.PositiveSmallIntegerField(default=18, verbose_name='年龄'),
      preserve_default=False,
    ),
  ]
