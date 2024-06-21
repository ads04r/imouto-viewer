from dateutil import parser
import requests, json, sys

import logging
logger = logging.getLogger(__name__)

def get_recent_gitea_commits(username, token, api_url, since=None):

	url = api_url + "/user/repos?token=" + token

	ret = []
	r = requests.get(url)

	for repo in json.loads(r.text):
		if not('updated_at' in repo):
			continue
		if not('html_url' in repo):
			continue
		if not('full_name' in repo):
			continue
		if not(since is None):
			repo_update = parser.parse(repo['updated_at'])
			if repo_update <= since:
				continue
		repo_url = repo['html_url']
		repo_id = repo['full_name']
		repo_api_url = api_url + "/repos/" + repo_id + "/commits?token=" + token
		rr = requests.get(repo_api_url)
		data = json.loads(rr.text)
		if isinstance(data, dict):
			continue
		for commit in data:
			if not('author' in commit):
				continue
			if commit['author'] is None:
				continue
			if not('username' in commit['author']):
				continue
			if commit['author']['username'] != username:
				continue
			item = {}
			item['time'] = parser.parse(commit['commit']['committer']['date'])
			if not(since is None):
				if item['time'] <= since:
					continue
			item['hash'] = commit['sha']
			item['comment'] = commit['commit']['message']
			item['repo_url'] = repo_url
			item['url'] = commit['html_url']
			item['stats'] = {}
			ret.append(item)

	return sorted(ret, key=lambda x: x['time'], reverse=True)

def get_recent_github_commits(username, since=None):

	url = "https://api.github.com/users/" + username + "/events"

	ret = []
	r = requests.get(url)

	for event in json.loads(r.text):

		if not('type' in event):
			continue
		if not(event['type'] == 'PushEvent'):
			continue
		if not('repo' in event):
			continue
		if not('payload' in event):
			continue
		if not('commits' in event['payload']):
			continue

		push_date = parser.parse(event['created_at'])
		repo_url = "https://github.com/" + event['repo']['name']

		if not(since is None):
			if push_date < since:
				continue

		for commit in event['payload']['commits']:

			item = {}

			item['hash'] = commit['sha']
			item['comment'] = commit['message']
			item['repo_url'] = repo_url
			commit_url = commit['url']

			rr = requests.get(commit_url)
			data = json.loads(rr.text)
			item['url'] = commit_url
			if 'html_url' in data:
				item['url'] = data['html_url']
			item['stats'] = data['stats']
			item['time'] = parser.parse(data['commit']['committer']['date'])

			ret.append(item)

	return sorted(ret, key=lambda x: x['time'], reverse=True)
