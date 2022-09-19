from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
from dateutil.parser import parse as dateparse
from viewer.models import *
import os, sys, datetime, pytz, twitter, json, requests

class Command(BaseCommand):
	"""
	Command for importing tweets. This functionality needs the TWITTER_API setting to be set.
	"""
	def add_arguments(self, parser):

		choices = []
		parser.add_argument("-u", "--username", action="store", dest="username", default="", help="A Twitter username.")

	def __resolve_urls(self, message):

		words = message.split(' ')
		for i in range(0, len(words)):
			if not('://' in words[i]):
				continue
			try:
				response = requests.head(words[i], allow_redirects=True)
				if response.status_code == 200:
					words[i] = response.url
			except:
				pass
		return ' '.join(words)

	def __resolve_all_tweets(self):

		for tweet in RemoteInteraction.objects.filter(type='microblogpost', message__icontains='://').order_by('-time'):
			msg = tweet.message
			if '://' in msg:
				proc_msg = self.__resolve_urls(msg)
				if proc_msg != msg:
					print(proc_msg)
					tweet.message = proc_msg
					tweet.save()

	def handle(self, *args, **kwargs):

		if kwargs['username'] == '':
			sys.stderr.write(self.style.ERROR("Must supply a Twitter username using the --username argument.\n"))
			sys.exit(1)

		api_key = settings.TWITTER_API
		api = twitter.Api(tweet_mode='extended', consumer_key=api_key['consumer_key'], consumer_secret=api_key['consumer_secret'], access_token_key=api_key['access_token'], access_token_secret=api_key['access_secret'])

		res = api.GetSearch(term=kwargs['username'], result_type='recent', return_json=True, include_entities=True, count=100)
		outgoing = []
		incoming = []
		for tweet in res['statuses']:
			if 'full_text' in tweet:
				tweet['full_text'] = self.__resolve_urls(tweet['full_text'])
			if tweet['user']['screen_name'] == kwargs['username']:
				if 'retweeted_status' in tweet:
					continue
				outgoing.append(tweet)
				continue
			for mention in tweet['entities']['user_mentions']:
				if mention['screen_name'] == kwargs['username']:
					incoming.append(tweet)
					continue

		for tweet in incoming:
			dt = dateparse(tweet['created_at'])
			addr = "https://twitter.com/" + tweet['user']['screen_name']
			try:
				t = RemoteInteraction.objects.get(type='microblogpost', incoming=True, address=addr, time=dt)
			except:
				t = RemoteInteraction(type='microblogpost', incoming=True, address=addr, time=dt, message=tweet['full_text'])
				t.save()

		for tweet in outgoing:
			dt = dateparse(tweet['created_at'])
			if len(tweet['entities']['user_mentions']) == 0:
				try:
					t = RemoteInteraction.objects.get(type='microblogpost', incoming=False, address='', time=dt)
				except:
					t = RemoteInteraction(type='microblogpost', incoming=False, address='', time=dt, message=tweet['full_text'])
					t.save()
			else:
				for target in tweet['entities']['user_mentions']:
					addr = "https://twitter.com/" + target['screen_name']
					try:
						t = RemoteInteraction.objects.get(type='microblogpost', incoming=False, address=addr, time=dt)
					except:
						t = RemoteInteraction(type='microblogpost', incoming=False, address=addr, time=dt, message=tweet['full_text'])
						t.save()

