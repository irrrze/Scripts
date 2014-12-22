# coding=utf-8
import os
from twitter import *
import bitly_api
import feedparser
from BeautifulSoup import *
import time
import random
import config

CONSUMER_KEY = config.twitter_consumer_key
CONSUMER_SECRET = config.twitter_consumer_secret
OAUTH_TOKEN = config.twitter_oauth_token
OAUTH_SECRET = config.twitter_oauth_secret
BITLY_TOKEN = config.bitly_token
RECORD_FILE = 'feedrecord.txt'
cb_url = config.cb_url

def get_last_id():
	last_id = 0
	try: 
		with open(RECORD_FILE, "r") as f:
			l = f.read().replace('\n', '')
			last_id = int(l)
	except: 
		print 'ERROR: %s not found\n' % RECORD_FILE
	print 'Last id is %s\n' % last_id
	return last_id

def set_last_id(val):
	try:
		with open(RECORD_FILE, "w") as f:
			f.write(str(val))
	except Exception, msg:
		print 'ERROR: update record failed. %s' % msg
	print 'Last id %s is recorded succesfully\n' % val

def random_sleep():
	time.sleep(random.randrange(1, 5, 1))

def generate_short_link(url):
	bitly = bitly_api.Connection(access_token=BITLY_TOKEN)
	short_link = ''
	try:
		data = bitly.shorten(url)
		short_link = data['url'][7:]
	except Exception, msg:
		print 'ERROR: shorten %s failed' % url
	return short_link	

def tweet_feed(url):
	last_id = int(get_last_id())
	marker = last_id
	feed = feedparser.parse(url)
	twitter = Twitter(auth=OAuth(
    	OAUTH_TOKEN, OAUTH_SECRET, CONSUMER_KEY, CONSUMER_SECRET))
	for e in feed.entries:
			title = e.title
			link = e.link
			feed_id = int(re.findall(r"\d+", link)[0])
			if feed_id <= last_id:
					print 'INFO: skip %s' % feed_id
					continue
			if feed_id >= marker:
					marker = int(feed_id)
			short_link = generate_short_link(link)
			content = '' 
			try:
				soup = BeautifulSoup(e.description)
				content = soup.find('div').getText()
				content = content.replace("\n", "")
				content = re.sub(r"感谢.*投递", " ", content)
			except Exception, msg:
				print 'ERROR: %s extract content failed. %s' % (feed_id, msg)
			tweet = ''
			if len(title) > 140:
				tweet = r'%s %s' % (title[:120], short_link)
			else:
				desc_len = 130 - 2 - len(title) - len(short_link)
				tweet = r'%s %s %s' % (title, content[:desc_len], short_link)
			try:
				print 'Tweeting %s %s' % (feed_id, title.encode('utf-8', 'ignore'))
				twitter.statuses.update(status = tweet)
			except Exception, msg:
				print 'ERROR: tweet failed. %s' % msg
			random_sleep()
	set_last_id(marker)

tweet_feed(cb_url)

