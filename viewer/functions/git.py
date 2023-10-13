from dateutil import parser
import requests, json, sys

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

	return ret
