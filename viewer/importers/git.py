import datetime, pytz

from viewer.functions.git import get_recent_github_commits, get_recent_gitea_commits
from viewer.models import GitCommit

import logging
logger = logging.getLogger(__name__)

def import_github_history(user, since=None):
	"""
	Calls the public Github API to determine a list of commits pushed by the user, and imports these
	as GitCommit objects.

	:return: A list of the new GitCommit objects that have been added.
	:rtype: list(GitCommit)
	"""
	if not 'USER_GITHUB' in user.profile.settings:
		return []
	username = user.profile.settings['USER_GITHUB']
	if since is None:
		last_commit = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
	else:
		last_commit = since
	ret = []
	for commit in get_recent_github_commits(username, since=last_commit):
		if commit['time'] <= last_commit:
			continue
		try:
			item = GitCommit(user=user, hash=commit['hash'], comment=commit['comment'].strip(), repo_url=commit['repo_url'], commit_date=commit['time'], additions=commit['stats']['additions'], deletions=commit['stats']['deletions'])
			item.save()
		except:
			item = None
		if item is None:
			continue
		ret.append(item)
	return ret

def import_gitea_history(user, since=None):
	"""
	Calls a Gitea API to determine a list of commits pushed by the user, and imports these
	as GitCommit objects.

	:return: A list of the new GitCommit objects that have been added.
	:rtype: list(GitCommit)
	"""
	if not 'USER_GITHUB' in user.profile.settings:
		return []
	try:
		username = user.profile.settings['GITEA_USER']
	except AttributeError:
		username = None
	try:
		token = user.profile.settings['GITEA_TOKEN']
	except AttributeError:
		token = None
	try:
		url = user.profile.settings['GITEA_URL']
	except AttributeError:
		url = None
	if username is None:
		return []
	if url is None:
		return []
	if token is None:
		return []

	if since is None:
		last_commit = pytz.utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))
	else:
		last_commit = since
	ret = []
	for commit in get_recent_gitea_commits(username, token, url, since=last_commit):
		if commit['time'] <= last_commit:
			continue
		try:
			item = GitCommit(user=user, hash=commit['hash'], comment=commit['comment'].strip(), repo_url=commit['repo_url'], commit_date=commit['time'], additions=None, deletions=None)
			item.save()
		except:
			item = None
		if item is None:
			continue
		ret.append(item)
	return ret
