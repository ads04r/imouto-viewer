from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from viewer.importers.git import import_github_history, import_gitea_history
import sys, datetime, pytz

class Command(BaseCommand):
	"""
	Command for calling the import github function from the CLI
	"""
	def add_arguments(self, parser):

		parser.add_argument("-u", "--user", action="store", dest="user_id", required=True, help="which user are we working with?")

	def handle(self, *args, **kwargs):

		try:
			user = User.objects.get(username=kwargs['user_id'])
		except:
			user = None
		if not user:
			sys.stderr.write(self.style.ERROR(str(kwargs['user_id']) + " is not a valid user on this system.\n"))
			sys.exit(1)
		try:
			last_commit = GitCommit.objects.filter(user=user).sort('-commit_date')[0].commit_date
		except:
			last_commit = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
		commits = sorted(import_github_history(user=user, since=last_commit) + import_gitea_history(user=user, since=last_commit), key=lambda x: x.commit_date, reverse=True)
		for commit in commits:
			sys.stderr.write(self.style.SUCCESS('Imported commit ' + commit.hash + ' in ' + commit.repo_url + '\n'))
