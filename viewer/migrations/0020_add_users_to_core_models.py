from django.db import migrations, models

def fill_users(apps, schema_editor):
	User = apps.get_model('auth', 'User')
	last_user = User.objects.order_by('-date_joined').first()
	for model_name in ['GitCommit', 'Location', 'Person', 'Photo', 'Event', 'LifePeriod', 'Month', 'Day', 'DataReading', 'RemoteInteraction', 'CalendarFeed', 'CalendarTask', 'CalendarAppointment', 'EventWorkoutCategory', 'AutoTag', 'LocationCategory']:
		model = apps.get_model('viewer', model_name)
		model.objects.all().update(user=last_user)

class Migration(migrations.Migration):

	dependencies = [
		("viewer", "0019_day_user_alter_day_unique_together"),
	]

	operations = [
		migrations.RunPython(fill_users),
		migrations.AlterField(model_name='GitCommit', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='Location', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='Person', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='Photo', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='Event', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='LifePeriod', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='Month', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='Day', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='DataReading', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='RemoteInteraction', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='CalendarFeed', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='CalendarTask', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='CalendarAppointment', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='EventWorkoutCategory', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='AutoTag', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
		migrations.AlterField(model_name='LocationCategory', name='user', field=models.ForeignKey(to='auth.User', on_delete=models.CASCADE)),
	]
