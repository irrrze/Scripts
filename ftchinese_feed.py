import feedparser
import chardet
import lxml.html
import PyRSS2Gen
import urllib2
import re
import socket
import datetime
from time import sleep
import config

output = config.rss_output
user_agent = config.user_agent
proxy = { "http" : config.proxy }
timeout = 20
socket.setdefaulttimeout(timeout)

feedMap = { 
	  "ftchinese" : { "url" : "http://www.ftchinese.com/rss/feed",
	  	       "tag_name" : "class",
	  	       "tag_attr" : "content",
		       "encode" : "utf-8",
		       "status" : "enabled"},
	  }

def grabdata(url):
	proxy_handler = urllib2.ProxyHandler(proxy)
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
		except Exception:
			if count == 4:
				print "error: grab %s" % url
			sleep(count)
			count += 1
	return [status, data]

def parsepage(url, info):
	[fetchstatus, htmlSource] = grabdata(url)
	if fetchstatus == False:
		return ""
	if info.has_key("encode"):
		encode = info["encode"]
	else:
		encode = chardet.detect(htmlSource)["encoding"]
		if encode == "GB2312" or encode == None:
			encode = "GBK"
	news = ""
	news_list = []
	content = None
	try:
		h = lxml.html.fromstring(unicode(htmlSource, encode, errors='ignore'))
		if info["tag_name"] == "id":
			content = h.get_element_by_id(info["tag_attr"])
			if content != None:
				content.make_links_absolute(info["url"])
				news = lxml.html.tostring(content, encoding='utf-8')
		elif info["tag_name"] == "class":
			contents = h.find_class(info["tag_attr"])
			for content in contents:
				if content != None:
					banners = content.find_class("banner")
					for banner in banners:
						parent = banner.getparent()
						parent.remove(banner)
					content.make_links_absolute(info["url"])
					news_list.append(lxml.html.tostring(content, encoding='utf-8'))
			news = "".join(news_list)
		else:
			content = None
		if info.has_key("tag_name2"):
			content2 = None
			news2 = ""
			if info["tag_name2"] == "id":
				content2 = h.get_element_by_id(info["tag_attr2"])
			elif info["tag_name2"] == "class":
				contents = h.find_class(info["tag_attr2"])
				if(len(contents) > 0):
					content2 = contents[0]
			else:
				content2 = None
			if content2 != None:
				content2.make_links_absolute(info["url"])
				news2 = lxml.html.tostring(content2, encoding='utf-8')
			else:
				news2 = ""
			news = "".join([news, news2])
	except Exception, msg:
		print "debug: error fetch %s\n%s" % (url, msg)
	return news

def genfeed(name, info):
	localurl = r'%s/%s.xml' % (output, name)
	proxy_handler = urllib2.ProxyHandler(proxy)
	print "debug: process %s" % name
	old_entries = []
	try:
		lfeed  = feedparser.parse(localurl)
		old_entries = lfeed.entries
	except Exception:
		lfeed = {}
		print "Debug: error parse %s" % localurl
	fetchstatus = False
	count = 0
	if lfeed.has_key("status") and lfeed.status == 200 and len(lfeed.entries) > 0:
		while fetchstatus == False and count < 5:
			try:
				d = feedparser.parse(info["url"], modified = lfeed.modified, agent=user_agent)
				fetchstatus = True
				if d.status == 304: 
					print "debug: %s no update!" % name
					return
			except Exception:
				if count == 4:
					print "debug: %d error parse %s" % (count, info["url"])
				sleep(count)
				count += 1
		if fetchstatus == False:
			return
	else:
		d = feedparser.parse(info["url"], agent=user_agent)
	items = []
	if(info.has_key("num")):
		entries = d.entries[:info["num"]]
	else:
		entries = d.entries
	hit_count = 0
	for e in entries:
		if e.has_key("author") == False:
			e.author = name
		if e.has_key("updated") == False:
			e.updated = datetime.datetime.now()
		if e.has_key("id") == False:
			e.id = PyRSS2Gen.Guid(e.link)
		hit_cache = False
		for oe in old_entries:
			try:
				if e.id == oe.id:
					e.description = oe.description
					hit_cache = True
					hit_count += 1;
					break
			except Exception:
				break
		if not hit_cache:
			e.description = parsepage(e.link, info)
		try:
			items.append(
				PyRSS2Gen.RSSItem(
				title = e.title,
				link = e.link,
				description = e.description,
				guid = e.id,
				pubDate = e.updated,
				author = e.author)) 
		except AttributeError:
			print "\n".join(["%s=%s" % (name, value) for name, value in e.items()])
	if hit_count == len(entries):
		print "info: no need to update"
		del items
		return
	if d.feed.has_key("lastbuilddate"):
		timestamp = d.feed.lastbuilddate
	elif d.feed.has_key("updated"):
		timestamp = d.feed.updated
	else:
		timestamp = datetime.datetime.now()
	if d.feed.has_key("title"):
		feedtitle = d.feed.title
	else:
		feedtitle = name
	if d.feed.has_key("link"):
		feedlink = d.feed.link
	else:
		feedlink = info["url"]
	if d.feed.has_key("description"):
		feeddes = d.feed.description
	else:
		feeddes = name
	PyRSS2Gen.RSS2(
		title = feedtitle,
		link = feedlink,
		description = feeddes,
		lastBuildDate = timestamp,
		items = items).write_xml(open("%s/%s.xml" % (output, name), "w"), encoding='utf-8')
	print "debug: %d entries created(%d cached)" % (len(items), hit_count)
	del items

""" main"""
for name, info in feedMap.items():
	if info.has_key("status") and info["status"] == "disabled": continue
	genfeed(name, info)

