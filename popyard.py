import feedparser
import chardet
import lxml.html
import PyRSS2Gen
import urllib2
import re
import socket
import datetime
from time import sleep
import BeautifulSoup
import sys
import traceback
import config

output = config.rss_output
user_agent = config.user_agent
proxy = { "http" : conifg.proxy }
timeout = 20
socket.setdefaulttimeout(timeout)

feedMap = { 
	  "popyard" : {
		  	  "url" : "http://www.popyard.org",
			  "encode" : "GBK",
			  "link_tag_name" : "class",
			  "link_tag_attr" : "link",
			  "tag_name" : "class",
			  "tag_attr" : "line_space",
			  "tag_filter_name" : "valign",
			  "tag_filter_value" : "top",
			  "status" : "enabled"
	  		}
	  }

def grabdata(url):
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
		except Exception as e:
			if count == 4:
				print "error: grab %s" % url
			sleep(count)
			count += 1
	return [status, data]

def parsepage(url, info, nextpage=False):
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
	content = None
	try:
		h = lxml.html.fromstring(unicode(htmlSource, encode, errors='ignore'))
		if info["tag_name"] == "id":
			content = h.get_element_by_id(info["tag_attr"])
			contents = [content]
		elif info["tag_name"] == "class":
#			contents = h.find_class(info["tag_attr"])
			pool = BeautifulSoup(unicode(htmlSource, encode, errors='ignore'))
			contents = pool.findAll('table', attrs={'width':'728'})
		else:
			content = None
		news_list = []
		remove_list = ["font_size", "title_tool", "comment", "pagination", "announce", "story_list"]
		remove_list2 = ["cheadline", "chead_info"]
		for content in contents:
			del content.td.attrs
			tds = content.td.findAll('td')
			for td in tds:
				if(td.attrs and 'bgcolor' in td.attrs and td.attrs['bgcolor'] == 'gray'): 
					td.decompose()
			imgs = content.td.findAll('img')
			for img in imgs:
				if img.has_key('border'):
					img['border'] = 0
				if img.has_key('width'):
					width = int(img['width'])
					if width < 300:
						img['width'] = width * 2
				if img.has_key('src') and 'www.china724.org' in img['src']:
						img.decompose()
			news_list.insert(0, unicode(content.td)[4:-5])
		if not nextpage:
			# paging process
			page_links = []
			h.make_links_absolute('http://www.popyard.com/cgi-mod/')
	        	sub_links = h.iterlinks()	
			link_pattern = re.compile(r'^http://www.popyard.\w{3}/cgi-mod/newspage.cgi\?num=\d+')
			for link in sub_links:
				(element, attribute, page_url, pos) = link
				if link_pattern.search(page_url) and page_url != url:
					print "debug: add subpage: %s" % page_url
					page_links.append(page_url)
			if len(page_links) > 0:
				print "deubg: %s has %d pages" % (url, len(page_links))
			for link in page_links:
				news_list.append(parsepage(link, info, True))
		news = "".join(news_list)
	except Exception, msg:
		print "debug: error fetch %s\n%s" % (url, msg)
		print '-'*60
	        traceback.print_exc(file=sys.stdout)
	        print '-'*60
	return news

def genfeed(name, info):
	localurl = r'%s/%s.xml' % (output, name)
	print "debug: process %s" % name
	try:
		lfeed  = feedparser.parse(localurl)
	except Exception:
		lfeed = {}
		print "Debug: error parse %s" % localurl
	fetchstatus = False
	links = []

	cat_url = info['url']
	print "debug: process %s" % cat_url
	[status, htmlSource] = grabdata(cat_url)
	if status == False:
		print "debug: failed to fetch %s, terminated" % cat_url
		return
	if info.has_key('encode'):
		htmlSource = unicode(htmlSource, info['encode'], errors='ignore')
	content = lxml.html.fromstring(htmlSource)
	content.make_links_absolute(info["url"])
	sub_links = content.iterlinks()
	links[len(links) : ] = sub_links
	link_pattern = re.compile(r'newspage.cgi\?num=\d+')
	date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
	count = 0
	items = []
	rss_items = []
	old_entries = lfeed.entries
	for link in links[:150]:
		(element, attribute, url, pos) = link
		if not link_pattern.search(url):
			continue
		news_title = element.text_content()
		if  news_title == "":
			continue
		news_link = url
		print "debug: process %s" % news_link
		news_description = u""
		news_date = datetime.datetime.now()
		hit_cache = False
		for oe in old_entries:
			if news_link == oe.link:
				hit_cache = True
				news_description = oe.description
				news_date = oe.date
				count += 1
				break

		if not hit_cache:
			print "not in cache"
			fetchstatus = True
			random_sleep()
			news_description = parsepage(news_link, info)
			if news_description == "":
				continue
		try:
			rss_item = PyRSS2Gen.RSSItem(
				title = news_title,
				link = news_link,
				description = news_description,
				guid = PyRSS2Gen.Guid(news_link),
				pubDate = news_date,
				author = name)
			item = news_date, rss_item
			items.append(item)
		except Exception, msg:
			print "append rss item error.\n%s" % msg
	if not fetchstatus:
		print "debug: no need to update"
		del items
		return
	for item in items:
		(news_date, rss_item) = item
		rss_items.append(rss_item)
	timestamp = datetime.datetime.now()
	feedtitle = name
	feedlink = info["url"]
	feeddes = name
	PyRSS2Gen.RSS2(
		title = feedtitle,
		link = feedlink,
		description = feeddes,
		lastBuildDate = timestamp,
		items = rss_items).write_xml(open("%s/%s.xml" % (output, name), "w"), encoding='utf-8')
	print "debug: %d entries created(%d cached)" % (len(items), count)
	del items
	del rss_items

def random_sleep():
	time.sleep(random.randrange(1, 5, 1))

""" main"""
for name, info in feedMap.items():
	if info.has_key("status") and info["status"] == "disabled": continue
	genfeed(name, info)

