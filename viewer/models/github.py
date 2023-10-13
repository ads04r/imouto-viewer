from django.db import models

class GitCommit(models.Model):
	repo_url = models.URLField()
	commit_date = models.DateTimeField()
	hash = models.SlugField(max_length=48)
	comment = models.TextField()
	additions = models.IntegerField()
	deletions = models.IntegerField()
