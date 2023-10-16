from django.core.management.base import BaseCommand
from viewer.importers import import_github_history, import_gitea_history
import sys, datetime, pytz

class Command(BaseCommand):
	"""
	Command for calling the import github function from the CLI
	"""
	def handle(self, *args, **kwargs):

		try:
			last_commit = GitCommit.objects.sort('-commit_date')[0].commit_date
		except:
			last_commit = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
		commits = sorted(import_github_history(since=last_commit) + import_gitea_history(since=last_commit), key=lambda x: x.commit_date, reverse=True)
		for commit in commits:
			sys.stderr.write(self.style.SUCCESS('Imported commit ' + commit.hash + ' in ' + commit.repo_url + '\n'))

