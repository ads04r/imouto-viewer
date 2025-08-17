from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

def fill_user_profiles(apps, schema_editor):

	UserProfile = apps.get_model('viewer', 'UserProfile')
	User = apps.get_model('auth', 'User')
	for user in User.objects.all():
		profile = UserProfile(user=user)
		profile.save()


class Migration(migrations.Migration):

    replaces = [('viewer', '0013_userprofile'), ('viewer', '0014_auto_20250817_2302')]

    dependencies = [
        ('viewer', '0012_remoteinteraction_contact'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('settings', models.JSONField(default=dict)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(
            code=fill_user_profiles,
        ),
        migrations.AlterField(
            model_name='UserProfile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
