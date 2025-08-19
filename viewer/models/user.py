from django.db import models
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

def create_new_userprofile():
	ret = {}
	return ret

class UserProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
	date_of_birth = models.DateField(null=True, blank=True)
	home_location = models.IntegerField(default=0)
	rdf_namespace = models.URLField(null=True, blank=True)
	settings = models.JSONField(default=create_new_userprofile, encoder=DjangoJSONEncoder)
	def __str__(self):
		return str(self.user)

@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
	if created:
		UserProfile.objects.create(user=instance)
	instance.profile.save()
