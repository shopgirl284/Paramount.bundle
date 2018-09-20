PREFIX = '/video/paramount'
TITLE = 'Paramount Network'
ART = 'art-default.jpg'
ICON = 'icon-default.jpg'
BASE_URL = 'http://www.paramountnetwork.com'

FULLEP_API = 'http://www.paramountnetwork.com/api/episodes/1/18'
RE_JSON = Regex('window.__DATA__ = (.+?)\n', Regex.DOTALL)

SEARCH = 'http://www.paramountnetwork.com/api/search?q=%s&searchFilter=site&rowsPerPage=16&pageNumber=0'
SEARCH_TYPE = ['Video', 'Episode', 'Series']

RE_SXX_EXX = Regex('season-(\d+)-ep-(\d+)')
RE_SXX_EXX2 = Regex('S(\d+) E(\d+)')

###################################################################################################
def Start():

    ObjectContainer.title1 = 'Paramount Network'
    DirectoryObject.thumb = R(ICON)
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'

####################################################################################################
@handler(PREFIX, TITLE, art=ART, thumb=ICON)
def MainMenu():

    oc = ObjectContainer()

    oc.add(DirectoryObject(key = Callback(VideoList, title="Full Episodes", url=FULLEP_API), title = "Full Episodes"))
    oc.add(DirectoryObject(key = Callback(Shows, title="All Shows", url=BASE_URL+'/shows'), title = "All Shows"))
    oc.add(InputDirectoryObject(key = Callback(SearchSections, title="Search"), title = "Search"))

    return oc

#####################################################################################
# This function produces the list of Shows from the json content of the show page
@route(PREFIX + '/shows')
def Shows(title, url):

    oc = ObjectContainer(title2=title)

    try:
        content = HTTP.Request(url, cacheTime=CACHE_1DAY).content
        json = JSON.ObjectFromString(RE_JSON.search(content).group(1))
    except:
        return ObjectContainer(header="Incompatible", message="Unable to find videos for %s." % (url))

    item_list = []

    for section in json['children']:

        try: section_title = section['props']['header']['title'].title()
        except: section_title = ''

        if section_title=="All Shows":
            item_list = section['props']['items']
            break

    for show in item_list:

        try: item_url = show['url']
        except: continue

        if not item_url.startswith('http://'):
            item_url = BASE_URL + item_url

        try: thumb = show['media']['image']['url']
        except: thumb = None

        if thumb and thumb.startswith('//'):
            thumb = 'http:' + thumb

        oc.add(DirectoryObject(
            key=Callback(Sections, title=show['meta']['header']['title'], url=item_url, thumb=thumb),
            title=show['meta']['header']['title'],
            thumb = Resource.ContentsOfURLWithFallback(url=thumb)
        ))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no results to list right now.")
    else:
        return oc

#####################################################################################
# This function produces the video sections from the json content on each main show page
# The filter data pulled includes the api url for each video section
@route(PREFIX + '/sections')
def Sections(title, url, thumb):

    oc = ObjectContainer(title2=title)
    show = title

    try:
        content = HTTP.Request(url, cacheTime=CACHE_1DAY).content
        json = JSON.ObjectFromString(RE_JSON.search(content).group(1))
    except:
        return ObjectContainer(header="Incompatible", message="Unable to find videos for %s." % (url))

    item_list = []

    for section in json['children']:

        try: section_title = section['props']['type']
        except: section_title = ''

        if section_title=="video-guide":
            item_list = section['props']['filters']['items']
            break

    for item in item_list:

        try: item_url = item['url']
        except: continue

        if not item_url.startswith('http://'):
            item_url = BASE_URL + item_url

        oc.add(DirectoryObject(
            key=Callback(VideoList, title=item['label'], url=item_url, show_title=show),
            title=item['label'],
            thumb = Resource.ContentsOfURLWithFallback(url=thumb)
        ))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no results to list right now.")
    else:
        return oc

####################################################################################################
# This function produces a video lists from api urls
@route(PREFIX + '/videolist')
def VideoList(title, url, show_title=''):

    oc = ObjectContainer(title2=title)

    try:
        json = JSON.ObjectFromURL(url)
    except:
        return ObjectContainer(header="Incompatible", message="Unable to find videos for %s." % (url))

    for video in json['items']:

        try: vid_url = video['url']
        except: continue

        if not vid_url.startswith('http://'):
            vid_url = BASE_URL + vid_url

        # catch any bad links that get sent here
        if 'bellator.spike.com' in vid_url:
            continue

        thumb = video['media']['image']['url']

        if thumb and thumb.startswith('//'):
            thumb = 'http:' + thumb

        try: title = video['meta']['subHeader']
        except: title = video['meta']['header']['title']

        if show_title:
            show = show_title
        else:
            show = video['meta']['label']

        try: (season, episode) = RE_SXX_EXX.search(vid_url).groups()
        except: 
            try: (season, episode) = RE_SXX_EXX2.search(video['meta']['label'][1]['title']).groups()
            except: (season, episode) = ('0', '0')

        oc.add(EpisodeObject(
            url = vid_url, 
            show = show,
            season = int(season) if season else None,
            index = int(episode) if episode else None,
            title = title, 
            thumb = Resource.ContentsOfURLWithFallback(url=thumb),
            originally_available_at = Datetime.ParseDate(video['meta']['date']),
            duration = Datetime.MillisecondsFromString(video['media']['duration']),
            summary = video['meta']['description']
        ))

    try: next_page = BASE_URL + json['loadMore']['url']
    except: next_page = None

    if next_page and len(oc) > 0:

        oc.add(NextPageObject(
            key = Callback(VideoList, title=title, url=next_page),
            title = 'Next Page ...'
        ))

    if len(oc) < 1:
        Log ('still no value for objects')
        return ObjectContainer(header="Empty", message="There are no unlocked videos available to watch.")
    else:
        return oc

####################################################################################################
# This function produces the types of search results (show, video, etc) returned from the search api
@route(PREFIX + '/searchsections')
def SearchSections(title, query):

    oc = ObjectContainer(title2=title)
    json_url = SEARCH % (String.Quote(query, usePlus=False))
    local_url = json_url + '0&activeTab=All'
    json = JSON.ObjectFromURL(local_url)
    i = 0
    search_list = json['response']['facetCounts']['facet_fields']['bucketName_s']

    for item in search_list:

        if item in SEARCH_TYPE and search_list[i+1]!=0:
            oc.add(DirectoryObject(key = Callback(Search, title=item, url=json_url, search_type=item), title = item))

        i = i+1

    return oc

####################################################################################################
# This function produces the show or video results for a each search section
@route(PREFIX + '/search', page=int)
def Search(title, url, page=0, search_type=''):

    oc = ObjectContainer(title2=title)
    local_url = '%s%s&activeTab=%s' % (url, page, search_type)
    json = JSON.ObjectFromURL(local_url)

    for item in json['response']['items']:

        try: item_url = item['url']
        except: continue

        # Skip bellator url that are not part of the URL service
        if not item_url.startswith(BASE_URL):
            continue

        result_type = item['type']
        item_title = item['meta']['header']['title'].replace('• ', '')

        thumb = item['media']['image']['url']

        if thumb and thumb.startswith('//'):
            thumb = 'http:' + thumb

        # For Shows
        if result_type == 'series':

            oc.add(DirectoryObject(
                key = Callback(Sections, title=item_title, url=item_url, thumb=thumb),
                title = item_title,
                thumb = Resource.ContentsOfURLWithFallback(url=thumb)
            ))

        # For Episodes and Video Clips
        else:
            label_list = item['meta']['label']

            # For Video Clips
			# video title is header field and show, season/episode and type are label fields
            if result_type=='video':
                show = label_list[0]['title']
                other_data = label_list[1]['title']
                i = 2

                while i<len(label_list):
                    other_data = '%s %s' % (other_data, label_list[i]['title'])
                    i=i+1

                try: (season, episode) = RE_SXX_EXX2.search(other_data).groups()
                except: (season, episode) = ('0', '0')

                full_title = '%s: %s' % (other_data, item_title)

            # For Episodes
            # Video title is subHeader field, season/episode is header field and show title is label field
            else:
                show = label_list
                full_title = '%s: %s' % (item_title, item['meta']['subHeader'])
                (season, episode) = RE_SXX_EXX2.search(item_title).groups()

            oc.add(EpisodeObject(
                url = item_url, 
                show = show, 
                title = full_title, 
                thumb = Resource.ContentsOfURLWithFallback(url=thumb),
                summary = item['meta']['description'], 
                season = int(season) if season else None, 
                index = int(episode) if episode else None,
                duration = Datetime.MillisecondsFromString(item['media']['duration']), 
                originally_available_at = Datetime.ParseDate(item['meta']['date'])
            ))

    if json['metadata']['startingRow']+16 < json['metadata']['numFound']:

        oc.add(NextPageObject(
            key = Callback(Search, title='Search', url=url, search_type=search_type, page=page+1),
            title = 'Next Page ...'
        ))

    if len(oc) < 1:
        return ObjectContainer(header="Empty", message="There are no results to list.")
    else:
        return oc
