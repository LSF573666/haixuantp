from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_face_verify_session_identity_fields'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FaceVerifySession',
        ),
        migrations.RemoveField(
            model_name='user',
            name='face_verified_at',
        ),
        migrations.RemoveField(
            model_name='user',
            name='id_card_number',
        ),
        migrations.RemoveField(
            model_name='user',
            name='identity_verified_at',
        ),
        migrations.RemoveField(
            model_name='user',
            name='is_face_verified',
        ),
        migrations.RemoveField(
            model_name='user',
            name='is_identity_verified',
        ),
        migrations.RemoveField(
            model_name='user',
            name='real_name',
        ),
    ]
