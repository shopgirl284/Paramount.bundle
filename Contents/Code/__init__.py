PREFIX = '/video/paramount'
TITLE = 'Paramount Network'
ART = 'art-default.jpg'
ICON = 'icon-default.png'
BASE_URL = 'http://www.paramountnetwork.com/'

# Pull the json from the HTML content to prevent any issues with redirects and/or bad urls
RE_MANIFEST_URL = Regex('var triforceManifestURL = "(.+?)";', Regex.DOTALL)
RE_MANIFEST = Regex('var triforceManifestFeed = (.+?);', Regex.DOTALL)

EXCLUSIONS = ['Bellator']
SEARCH ='http://search.paramountnetwork.com/solr/paramountnetwork/select?q=%s&wt=json&defType=edismax&start='
SEARCH_TYPE = ['Video', 'Episode', 'Series']
ENT_LIST = ['ent_m249', 'ent_m252']

RE_SXX_EXX = Regex('season-(\d+)-ep-(\d+)')

####################################################################################################
def Start():

	ObjectContainer.title1 = 'Paramount Network'
	DirectoryObject.thumb = R(ICON)
	HTTP.CacheTime = CACHE_1HOUR
	HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'

####################################################################################################
@handler(PREFIX, TITLE, art=ART, thumb=ICON)
def MainMenu():

	oc = ObjectContainer()
	feed_list = GetFeedList(BASE_URL+'episodes')
	for json_feed in feed_list:
		#Log('the value of json_feed is %s' %json_feed)
		if '/ent_m249/' in json_feed:
			oc.add(DirectoryObject(key = Callback(ShowVideos, title="Full Episodes", url=json_feed), title = "Full Episodes"))
			break
	oc.add(DirectoryObject(key = Callback(FeedMenu, title="Shows", url=BASE_URL+'shows'), title = "Shows"))
	oc.add(InputDirectoryObject(key = Callback(SearchSections, title="Search"), title = "Search"))

	return oc

####################################################################################################
# This function pulls the json feeds in the ENT_LIST for any page
# ENT 249 is used for lost of things so you must specify when pulling data from it.
@route(PREFIX + '/feedmenu')
def FeedMenu(title, url, thumb='', season=False):
    
	oc = ObjectContainer(title2=title)
	feed_title = title
	feed_list = GetFeedList(url)
	if feed_list<1:
		return ObjectContainer(header="Incompatible", message="Unable to find video feeds for %s." %url)
    
	for json_feed in feed_list:

		# Split feed to get ent code
		try: ent_code = json_feed.split('/feeds/')[1].split('/')[0]
		except:  ent_code = ''

		if ent_code not in ENT_LIST:
			continue
			
		# Create a menu for show list feed (ent_m249)
		if ent_code=='ent_m249' and feed_title=="Shows":
			for item in JSON.ObjectFromURL(json_feed, cacheTime = CACHE_1DAY)['result']['data']['items']:
				thumb = item['media']['image']['url']
				if thumb.startswith('//'):
					thumb = 'http:' + thumb
				if 'http://www.bellator.com/' in item['url']:
					continue
				oc.add(DirectoryObject(key=Callback(FeedMenu, title=item['meta']['title'], url=BASE_URL+item['url'], thumb=thumb),
					title=item['meta']['title'],
					thumb = Resource.ContentsOfURLWithFallback(url=thumb)
				))
				        
		# Create menu for individual shows by season or section (ent_m252)
		elif ent_code == 'ent_m252':
			json = json = JSON.ObjectFromURL(json_feed, cacheTime = CACHE_1DAY)
			if not season:
				for season in json['result']['data']['seasons']:
					oc.add(DirectoryObject(
						key = Callback(FeedMenu, title=season['label'], url=season['url'], thumb=thumb, season=True),
						title = season['label'],
						thumb = Resource.ContentsOfURLWithFallback(url=thumb)
					))
			else:
				for section in json['result']['data']['filters']:
					oc.add(DirectoryObject(
						key = Callback(ShowVideos, title=section['label'], url=section['url']),
						title = section['label'],
						thumb = Resource.ContentsOfURLWithFallback(url=thumb)
					))

		else:
			Log('the json feed %s does not have a listing here' %json_feed)
			continue
            
	if len(oc) < 1:
		return ObjectContainer(header="Empty", message="There are no results to list.")
	else:
		return oc
#######################################################################################
# This function produces the videos listed in a json feed under items
@route(PREFIX + '/showvideos')
def ShowVideos(title, url):

    oc = ObjectContainer(title2=title)
    json = JSON.ObjectFromURL(url)
    # Currently all video results are under result/data/items
    try: videos = json['result']['data']['items']
    except: return ObjectContainer(header="Empty", message="There are no videos to list right now.")
    
    for video in videos:

        try: vid_url = video['url']
        except: continue

        # catch any bad links that get sent here
        if 'bellator.spike.com' in vid_url:
            continue

        try: thumb = video['media']['image']['url']
        except:
			try: thumb = video['image'][0]['url']
			except: thumb = None
        if thumb and thumb.startswith('//'):
            thumb = 'http:' + thumb

        try: title = video['meta']['title']
        except: title = video['title']
        try: description = video['meta']['description']
        except: description = video['description']
        try: show = video['meta']['showTitle']
        except: show = ''
        try: (season, episode) = RE_SXX_EXX.search(vid_url).groups()
        except: (season, episode) = (None, None)
        
        try: date = Datetime.ParseDate(video['meta']['airDate'])
        except: date = Datetime.ParseDate(video['displayDate'])

        # Duration for Individual shows are integers/floats and full episode feeds are strings
        try: duration = Datetime.MillisecondsFromString(video['meta']['duration'])
        except:
			try: duration = Datetime.MillisecondsFromString(video['duration'])
			except: duration =None

        oc.add(EpisodeObject(
            url = vid_url, 
            show = show,
            season = int(season) if season else None,
            index = int(episode) if episode else None,
            title = title, 
            thumb = Resource.ContentsOfURLWithFallback(url=thumb),
            originally_available_at = date,
            duration = duration,
            summary = description
        ))

    try: next_page = json['result']['data']['nextPageURL']
    except:
		try: next_page = json['result']['data']['loadMore']['url']
		except: next_page = None

    if next_page and len(oc) > 0:

        oc.add(NextPageObject(
            key = Callback(ShowVideos, title=title, url=next_page),
            title = 'Next Page ...'
        ))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no unlocked videos available to watch.")
    else:
        return oc
####################################################################################################
# This function produces the types of results (show, video, etc) returned from a search
@route(PREFIX + '/searchsections')
def SearchSections(title, query):
    
    oc = ObjectContainer(title2=title)
    json_url = SEARCH %String.Quote(query, usePlus = False)
    local_url = json_url + '0&facet=on&facet.field=bucketName_s'
    json = JSON.ObjectFromURL(local_url)
    i = 0
    search_list = json['facet_counts']['facet_fields']['bucketName_s']
    for item in search_list:
        if item in SEARCH_TYPE and search_list[i+1]!=0:
            oc.add(DirectoryObject(key = Callback(Search, title=item, url=json_url, search_type=item), title = item))
        i=i+1

    return oc
####################################################################################################
# This function produces the results for a search under each search type
@route(PREFIX + '/search', start=int)
def Search(title, url, start=0, search_type=''):

    oc = ObjectContainer(title2=title)
    local_url = '%s%s&fq=bucketName_s:%s' %(url, start, search_type)
    json = JSON.ObjectFromURL(local_url)

    for item in json['response']['docs']:

        result_type = item['bucketName_s']
        title = item['title_t']
        full_title = '%s: %s' % (result_type, title)

        try: item_url = item['url_s']
        except: continue
        # Skip bellator url that are not part of the URL service
        if not item_url.startswith(BASE_URL):
            continue

        # For Shows
        if result_type == 'Series':

            oc.add(DirectoryObject(
                key = Callback(FeedMenu, title=item['title_t'], url=item_url, thumb=item['imageUrl_s']),
                title = full_title,
                thumb = Resource.ContentsOfURLWithFallback(url=item['imageUrl_s'])
            ))

        # For Episodes and ShowVideo(video clips)
        else:
            try: season = int(item['seasonNumber_s'].split(':')[0])
            except: season = None

            try: episode = int(item['episodeNumber_s'])
            except: episode = None

            try: show = item['seriesTitle_t']
            except: show = None

            try: summary = item['description_t']
            except: summary = None

            try: duration = Datetime.MillisecondsFromString(item['duration_s'])
            except: duration = None

            oc.add(EpisodeObject(
                url = item_url, 
                show = show, 
                title = full_title, 
                thumb = Resource.ContentsOfURLWithFallback(url=item['imageUrl_s']),
                summary = summary, 
                season = season, 
                index = episode, 
                duration = duration, 
                originally_available_at = Datetime.ParseDate(item['contentDate_dt'])
            ))

    if json['response']['start']+10 < json['response']['numFound']:

        oc.add(NextPageObject(
            key = Callback(Search, title='Search', url=url, search_type=search_type, start=start+10),
            title = 'Next Page ...'
        ))

    if len(oc) < 1:
        return ObjectContainer(header="Empty", message="There are no results to list.")
    else:
        return oc
####################################################################################################
# This function pulls the list of json feeds from a manifest
@route(PREFIX + '/getfeedlist')
def GetFeedList(url):
    
	feed_list = []
	# In case there is an issue with the manifest URL, we then try just pulling the manifest data
	try: content = HTTP.Request(url, cacheTime=CACHE_1DAY).content
	except: content = ''
	if content:
		try: zone_list = JSON.ObjectFromURL(RE_MANIFEST_URL.search(content).group(1))['manifest']['zones']
		except:
			try:
				zone_data = RE_MANIFEST_FEED.search(content).group(1)
				zone_list = JSON.ObjectFromString(zone_data)['manifest']['zones']
			except: zone_list = []
			    
		for zone in zone_list:
			if zone in ('header', 'footer', 'ads-reporting', 'ENT_M171'):
				continue
			json_feed = zone_list[zone]['feed']
			feed_list.append(json_feed)
			#Log('the value of feed_list is %s' %feed_list)
			
	return feed_list