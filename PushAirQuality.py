from twitter import *
from pushbullet import PushBullet
import config

CONSUMER_KEY = config.twitter_consumer_key
CONSUMER_SECRET = config.twitter_consumer_secret
OAUTH_TOKEN = config.twitter_oauth_token
OAUTH_SECRET = config.twitter_oauth_secret
pb_api_key = config.pb_api_key


twitter = Twitter(auth=OAuth(
OAUTH_TOKEN, OAUTH_SECRET, CONSUMER_KEY, CONSUMER_SECRET))
tweets = twitter.statuses.user_timeline(screen_name="CGShanghaiAir", count=1)
text = tweets[0]['text']
pm25 = text.split(";")[3]
if pm25 > 90:
	pb = PushBullet(pb_api_key)
	nexus6p = pb.get_device('Huawei Nexus 6P')
	nexus6p.push_note('Shanghai Air Quality', text)










