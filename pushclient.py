import lxml.html
import urllib2
import re
import random
import time
from pushbullet import PushBullet
from time import sleep
import config

pb_api_key = config.pb_api_key
user_agent = config.user_agent
n6_gb_url = 'https://play.google.com/store/devices/details/Nexus_6_64GB_Cloud_White?id=nexus_6_white_64gb'
items = { 
	  "n1" : { "url" : "https://play.google.com/store/devices/details/Nexus_6_64GB_Cloud_White?id=nexus_6_white_64gb",
	  	       "sku" : "Nexus 6 (64GB, Cloud White)"},
	  "n2" : { "url" : "https://play.google.com/store/devices/details/Nexus_6_32GB_Cloud_White?id=nexus_6_white_32gb",
	  	       "sku" : "Nexus 6 (32GB, Cloud White)"},
	  "n3" : { "url" : "https://play.google.com/store/devices/details/Nexus_6_64GB_Midnight_Blue?id=nexus_6_blue_64gb",
	  	       "sku" : "Nexus 6 (64GB, Midnight Blue)"},
	  "n4" : { "url" : "https://play.google.com/store/devices/details/Nexus_6_32GB_Midnight_Blue?id=nexus_6_blue_32gb",
	  	       "sku" : "Nexus 6 (32GB, Midnight Blue)"},
	  }


def grabdata(url):
#	proxy_handler = urllib2.ProxyHandler(proxy)
#	opener = urllib2.build_opener(proxy_handler)
	opener = urllib2.build_opener()
	opener.addheaders = [('User-agent', user_agent)]
	status = False
	count = 0
	data = ''
	while status == False and count < 5:
		try:
			usock = opener.open(url)
			data = usock.read()
			usock.close()
			def checkRefresh(string):
				pattern = re.compile(r'http-equiv="refresh"')
				return pattern.search(string) != None
			if checkRefresh(data):
				import ClientCookie
				sock = ClientCookie.build_opener(ClientCookie.HTTPEquivProcessor,
						 ClientCookie.HTTPRefreshProcessor
						 )
				ClientCookie.install_opener(sock)
				data = ClientCookie.urlopen(url).read()
			status = True
		except Exception, msg:
			if count == 4:
				print "error: grab %s\n%s" % (url, msg)
			sleep(count)
			count += 1
	return [status, data]

def parsepage(url):
	[fetchstatus, htmlSource] = grabdata(url)
	if fetchstatus == False:
		return ""
	news = ""
	news_list = []
	content = None
	encode = 'UTF-8'
	try:
		h = lxml.html.fromstring(unicode(htmlSource, encode, errors='ignore'))
		contents = h.find_class('inventory-info')
		for content in contents:
			if content != None:
#				news_list.append(lxml.html.tostring(content, encoding='utf-8'))
				news_list.append(content.text_content())
			news = "".join(news_list)
	except Exception, msg:
		print "debug: error fetch %s\n%s" % (url, msg)
	return news

def random_sleep():
	time.sleep(random.randrange(1, 5, 1))

'''main'''
pb = PushBullet(pb_api_key)
#print(pb.devices)
nexus5 = pb.devices[0]
for title, info in items.items():
	inventory = parsepage(info['url'])
	print "%s %s" % (info['sku'], inventory)
	if not 'out of inventory' in inventory:
		nexus5.push_note(info['sku'], inventory)
#	else:
#		nexus5.push_note(info['sku'], 'still no luck:(')
	random_sleep()

#inventory = parsepage(n6_url)
#print inventory

#success, push = pb.push_note("n6 white 64gb", inventory)
