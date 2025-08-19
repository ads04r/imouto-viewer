from django.db import migrations, models

def fill_users(apps, schema_editor):
        User = apps.get_model('auth', 'User')
        last_user = User.objects.order_by('-date_joined').first()
        for model_name in ['ImportedFile', 'Media', 'MediaEvent', 'PhotoCollage', 'Questionnaire', 'WatchedDirectory', 'Year']:
                model = apps.get_model('viewer', model_name)
                model.objects.all().update(user=last_user)

class Migration(migrations.Migration):

	dependencies = [
		("viewer", "0021_importedfile_user_media_user_mediaevent_user_and_more"),
	]

	operations = [
                migrations.RunPython(fill_users),
                migrations.AlterField(model_name='ImportedFile', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
                migrations.AlterField(model_name='Media', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
                migrations.AlterField(model_name='MediaEvent', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
                migrations.AlterField(model_name='PhotoCollage', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
                migrations.AlterField(model_name='Questionnaire', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
                migrations.AlterField(model_name='WatchedDirectory', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
                migrations.AlterField(model_name='Year', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
	]
