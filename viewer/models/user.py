from django.db import models
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	settings = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
	def __str__(self):
		return str(self.user)

@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
	if created:
		UserProfile.objects.create(user=instance)
	instance.userprofile.save()
