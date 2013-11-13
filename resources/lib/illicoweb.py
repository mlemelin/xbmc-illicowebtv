# -*- coding: utf-8 -*-

import os
import re
import sys
import cookielib
import urllib
import urllib2
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
import simplejson

from urllib import quote_plus, unquote_plus
from traceback import print_exc

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs
from urlparse import urlparse

ADDON = xbmcaddon.Addon(id='plugin.video.illicoweb')
ADDON_NAME = ADDON.getAddonInfo( "name" )
ADDON_VERSION = "3"
ADDON_CACHE = xbmc.translatePath( ADDON.getAddonInfo( "profile" ) )
CACHE_EXPIRE_TIME = float( ADDON.getSetting( "expiretime" ).replace( "0", ".5" ).replace( "25", "0" ) )

LangXBMC    = xbmc.getLocalizedString

username = ADDON.getSetting( "username" )
password = ADDON.getSetting( "password" )
profile = xbmc.translatePath(ADDON.getAddonInfo('profile'))
home = xbmc.translatePath(ADDON.getAddonInfo('path'))
language = ADDON.getLocalizedString
icon = os.path.join(home, 'icon.png')

FAVOURITES_XML = os.path.join( profile, "favourites.xml" )

cookie_file = os.path.join(profile, 'cookie_file')
cookie_jar = cookielib.LWPCookieJar(cookie_file)

DEBUG = ADDON.getSetting('debug')

def addon_log(string):
    if DEBUG == 'true':
        xbmc.log("[Illicoweb-%s]: %s" %(ADDON_VERSION, string))

def getRequest(url, data=None, headers=None):
    if not xbmcvfs.exists(cookie_file):
        addon_log('Creating cookie_file!')
        cookie_jar.save()
    if headers is None:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'http://illicoweb.videotron.com'}
    cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
    urllib2.install_opener(opener)
    try:
        req = urllib2.Request(url,data,headers)
        response = urllib2.urlopen(req)
        data = response.read()
        cookie_jar.save(cookie_file, ignore_discard=True, ignore_expires=False)
        response.close()
        addon_log("getRequest : %s" %url)
        #addon_log(response.info())
        #if response.geturl() != url:
            #addon_log('Redirect URL: %s' %response.geturl())
        return data
    except urllib2.URLError, e:
        reason = None
        addon_log('We failed to open "%s".' %url)
        if hasattr(e, 'reason'):
            reason = str(e.reason)
            addon_log('We failed to reach a server.')
            addon_log('Reason: '+ reason)
        if hasattr(e, 'code'):
            reason = str(e.code)
            addon_log( 'We failed with error code - %s.' % reason )
            if 'highlights.xml' in url:
                return
        if reason:
            xbmc.executebuiltin("XBMC.Notification("+language(30015)+","+language(30019)+reason+",10000,"+icon+")")
        return  

def getWatched():
    watched = {}
    try:
        watched_db = os.path.join( ADDON_CACHE, "watched.db" )
        if os.path.exists( watched_db ):
            watched = eval( open( watched_db ).read() )
    except:
        print_exc()
    return watched

def setWatched( strwatched, remove=False, refresh=True ):
    if not strwatched: return
    
    # all strings must be unicode!!
    if isinstance(strwatched, str):
        strwatched = strwatched.decode('utf-8')

    try:
        watched_db = os.path.join( ADDON_CACHE, "watched.db" )
        if os.path.exists( watched_db ):
            watched = eval( open( watched_db ).read() )

        url, label = strwatched.split( "*" )

        watched[ url ] = watched.get( url ) or []
        # add to watched
        if label not in watched[ url ]:
            watched[ url ].append( label )

        # remove from watched
        if remove and label in watched[ url ]:
            del watched[ url ][ watched[ url ].index( label ) ]

        file( watched_db, "w" ).write( "%r" % watched )
    except:
        print_exc()
    if refresh:
        xbmc.executebuiltin( 'Container.Refresh' )
 
if re.search( '(GetCarrousel|"carrousel")', sys.argv[ 2 ] ):
    from GuiView import GuiView as viewtype
else:
    from PluginView import PluginView as viewtype 

class Main( viewtype ):
    def __init__( self ):
        viewtype.__init__( self )
        self.args = Info()
        self.watched = getWatched()

        if self.args.isempty():
            self._login()
            self._add_directory_root()

        elif self.args.setwatched or self.args.setunwatched:
            strwatched = self.args.setwatched or self.args.setunwatched
            if self.args.all:
                url, label = strwatched.split( "*" )
                seasonNo = url[url.rfind(',')+1:]
                url = '/' + url[:url.rfind(',')]
                data = self._getShowJSON(url)
                
                seasons = simplejson.loads(data)['body']['SeasonHierarchy']['seasons']

                # [body][SeasonHierarchy][seasons] seasons
                for i in seasons:
                    #addon_log(i['seasonNo'] + ' ==? ' + seasonNo)
                    if(str(i['seasonNo']) == seasonNo):
                        for ep in i['episodes']:
                            setWatched( ep['orderURI'] + '*' + ep['title'], bool( self.args.setunwatched ), False)

                # [body][main] seasons
                i = simplejson.loads(data)['body']['main']
                if(str(i['seasonNo']) == seasonNo):
                    for ep in i['episodes']:
                        setWatched( ep['orderURI'] + '*' + ep['title'], bool( self.args.setunwatched ), False)
                
                xbmc.executebuiltin( 'Container.Refresh' )
            else: setWatched( strwatched, bool( self.args.setunwatched ) )

        elif self.args.addtofavourites or self.args.removefromfavourites:
            #turn dict back into url, decode it and format it in xml
            f = unquote_plus( self.args.addtofavourites or self.args.removefromfavourites )
            f = parse_qs(urlparse('?' + f.replace( ", ", "&" ).replace('"','%22')).query)
            favourite = '<favourite label="%s" category="%s" url="%s" />' % (unquote_plus(f['label'][0]), f['category'][0], f['url'][0])

            if os.path.exists( FAVOURITES_XML ):
                favourites = open( FAVOURITES_XML ).read()
            else:
                favourites = '<favourites>\n</favourites>\n'
            if self.args.removefromfavourites or favourite not in favourites:
                if self.args.removefromfavourites:
                    addon_log('Removing %s from favourites' % favourite)
                    favourites = favourites.replace( '  %s\n' % favourite, '' )
                    refresh = True
                else:
                    favourites = favourites.replace( '</favourites>', '  %s\n</favourites>' % (favourite))
                    refresh = False
                file( FAVOURITES_XML, "w" ).write( favourites )
                if refresh:
                    if favourites == '<favourites>\n</favourites>\n':
                        try: os.remove( FAVOURITES_XML )
                        except: pass
                        xbmc.executebuiltin( 'Action(ParentDir)' )
                        xbmc.sleep( 1000 )
                    xbmc.executebuiltin( 'Container.Refresh' )
        
        elif self.args.favoris:
            self._add_directory_favourites()                    
                    
        elif self.args.live:
            self._playLive(unquote_plus(self.args.live).replace( " ", "+" ))

        elif self.args.episode:
            self._checkCookies()
            self._playEpisode(unquote_plus(self.args.episode).replace( " ", "+" ))

        elif self.args.channel:
            url = unquote_plus(self.args.channel).replace( " ", "+" )

            shows, fanart, livelist = self._getShows(url)
            listitems = []
            for i in shows:
                if 'submenus' in i:
                    for show in i['submenus']:
                        self._addShowToChannel(show, listitems, fanart)
                else:
                    self._addShowToChannel(i, listitems, fanart)
            
            if listitems:
                # Sort list by ListItem Label
                listitems = self.natural_sort(listitems, False) 

            if len(listitems) == 0:
                live = livelist[0][0]
                self._playLive(live[live.find('"'):].replace('"',""))
                return
                
            listitems = livelist + listitems
            OK = self._add_directory_items( listitems )
            self._set_content( OK, "movies", False )

        elif self.args.show:
            OK = False
            listitems = self._getSeasons(unquote_plus(self.args.show).replace( " ", "+" ))
            
            if listitems:
                from operator import itemgetter
                listitems = self.natural_sort(listitems, True)
                OK = self._add_directory_items( listitems )
            self._set_content( OK, "movies", False )

        elif self.args.season:
            url = unquote_plus(self.args.season).replace( " ", "+" )
            season = url[url.rfind(',') + 1:]
            url = url[:url.rfind(',')]

            data = self._getShowJSON(url)
            self._addEpisodesToSeason(data, season)

    def _addChannel(self, listitems, i, url):
        OK = False                
        try:
            label = i['name']
            episodeUrl = i['link']['uri']

            uri = sys.argv[ 0 ]
            item = ( label, '', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/logos/' + i['image'])
            url = url %( uri, episodeUrl  )
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/logos/' + i['image'] )
            listitem.setProperty( "fanart_image", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/presse1.jpg') #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/channels/' + ep['largeLogo'])
            
            self._add_context_menu( label, episodeUrl, 'channel', listitem, False, True )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()


        
    def _addLiveChannel(self, listitems, i, url, fanart):
        OK = False                
        try:
            label = '-- En Direct / Live TV --' #i['name']
            episodeUrl = i['orderURI'] 
            uri = sys.argv[ 0 ]
            item = ( label, '', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/logos/' + i['image'])
            url = url %( uri, episodeUrl  )
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/logos/' + i['image'] )
            #listitem.setProperty( "fanart_image", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/presse1.jpg') #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/channels/' + ep['largeLogo'])
            listitem.setProperty( "fanart_image", fanart)
            
            self._add_context_menu( i['name'] + ' - Live', episodeUrl, 'live', listitem, False, True )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
            
    def _addEpisodesToSeason(self, data, season):
        OK = False
        listitems = self._getEpisodes(data, season)

        if listitems:
            listitems = self.natural_sort(listitems, True)
            OK = self._add_directory_items( listitems )
        self._set_content( OK, "movies", False )
    
    def _addEpisodes(self, ep, listitems):
        label = ep['title']
        seasonUrl = ep['orderURI']
        OK = False
        try:
            uri = sys.argv[ 0 ]
            item = ( label,     '', 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/'  + ep['image']) #'DefaultAddonSubtitles.png')
            url = '%s?episode="%s"' %( uri, unquote_plus(seasonUrl.replace( " ", "+" ) ) )
            
            infoLabels = {
                "tvshowtitle": label,
                "title":       label
                #"genre":       genreTitle,
                #"plot":        episode[ "Description" ] or "",
                #"season":      int(season) or -1
                #"episode":     episode[ "EpisodeNumber" ] or -1,
                #"year":        int( episode[ "Year" ] or "0" ),
                #"Aired":       episode[ "AirDateLongString" ] or "",
                #"mpaa":        episode[ "Rating" ] or "",
                #"duration":    episode[ "LengthString" ] or "",
                #"studio":      episode[ "Copyright" ] or "",
                #"castandrole": scraper.setCastAndRole( episode ) or [],
                #"writer":      episode[ "PeopleWriter" ] or episode[ "PeopleAuthor" ] or "",
                #"director":    episode[ "PeopleDirector" ] or "",
            }
            
            watched = label in self.watched.get(seasonUrl, [] )
            overlay = ( xbmcgui.ICON_OVERLAY_NONE, xbmcgui.ICON_OVERLAY_WATCHED )[ watched ]
            infoLabels.update( { "playCount": ( 0, 1 )[ watched ], "overlay": overlay } )

            listitem = xbmcgui.ListItem( *item )
            listitem.setInfo( "Video", infoLabels )
            
            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/' + ep['image'] )
            listitem.setProperty( "fanart_image", xbmc.getInfoLabel( "ListItem.Property(fanart_image)" )) #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/' + ep['image'])
            
            #set property for player set watched
            strwatched = "%s*%s" % ( seasonUrl, label )
            listitem.setProperty( "strwatched", strwatched )
            listitem.setProperty( "playLabel", label )
            
            self._add_context_menu(  label, unquote_plus(seasonUrl.replace( " ", "+" ) ), 'episode', listitem, watched )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()

    def _addSeasonsToShow(self, i, listitems, title=False):
        label = 'Saison ' + str(i['seasonNo'])
        if title: label = '%s - %s' % (i['title'], label)
        seasonUrl = i['link']['uri'] + ',' + str(i['seasonNo'])

        OK = False
        try:
            uri = sys.argv[ 0 ]
            thumb = 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/' + i['image']
            item = ( label,     '',  thumb)
            url = '%s?season="%s"' %( uri, seasonUrl )

            listitem = xbmcgui.ListItem( *item )
            infoLabels = {
                "tvshowtitle": label,
                "title":       label
                #"genre":       genre,
                #"year":        int( year.split()[ 0 ] ),
                #"tagline":     ( STRING_FOR_ALL, "" )[ bool( GeoTargeting ) ],
                #"duration":    emission.get( "CategorieDuree" ) or "",
                #"episode":     NombreEpisodes,
                #"season":      -1,
                #"plot":        emission.get( "Description" ) or "",
                #"premiered":   emission.get( "premiered" ) or "",
                }
            
            watched = 0
            for episode in i['episodes']:
                if episode['title'] in self.watched.get(episode['orderURI'], [] ):
                    watched += 1
            NombreEpisodes = int( i['size'] or "1")
            unwatched = NombreEpisodes - watched
            addon_log ('Total: %s - Watched: %s = Unwatched: %s' % (str(NombreEpisodes), str(watched),str(unwatched)))

            listitem.setProperty( "WatchedEpisodes", str( watched ) )
            listitem.setProperty( "UnWatchedEpisodes", str( unwatched ) )

            playCount = ( 0, 1 )[ not unwatched ]
            overlay = ( xbmcgui.ICON_OVERLAY_NONE, xbmcgui.ICON_OVERLAY_WATCHED )[ playCount ]
            infoLabels.update( { "playCount": playCount, "overlay": overlay } )
            
            listitem.setInfo( "Video", infoLabels )

            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/thumb/' + i['image'] )
            listitem.setProperty( "fanart_image", xbmc.getInfoLabel( "ListItem.Property(fanart_image)" )) #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/' + i['image'])
            
            self._add_context_menu( i['title'], seasonUrl, 'season', listitem, not unwatched )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
    
    
    def _addShowToChannel(self, season, listitems, fanart, url=None):
        label = season['label']
        if label=='Home':
            return
        OK = False                
        try:
            showUrl = url or season['link']['uri']
            uri = sys.argv[ 0 ]
            item = ( label,     '')
            url = '%s?show="%s"' %( uri, showUrl  )
            listitem = xbmcgui.ListItem( *item )

            '''infoLabels = {
                "tvshowtitle": label,
                "title":       label
                #"genre":       genre,
                #"year":        int( year.split()[ 0 ] ),
                #"tagline":     ( STRING_FOR_ALL, "" )[ bool( GeoTargeting ) ],
                #"duration":    emission.get( "CategorieDuree" ) or "",
                #"episode":     NombreEpisodes,
                #"season":      -1,
                #"plot":        emission.get( "Description" ) or "",
                #"premiered":   emission.get( "premiered" ) or "",
                }
            
            watched = len( self.watched.get( showUrl ) or [] )
            NombreEpisodes = int( season['size'] or "1" )
            unwatched = NombreEpisodes - watched

            listitem.setProperty( "WatchedEpisodes", str( watched ) )
            listitem.setProperty( "UnWatchedEpisodes", str( unwatched ) )

            playCount = ( 0, 1 )[ not unwatched ]
            overlay = ( xbmcgui.ICON_OVERLAY_NONE, xbmcgui.ICON_OVERLAY_WATCHED )[ playCount ]
            infoLabels.update( { "playCount": playCount, "overlay": overlay } )
            
            listitem.setInfo( "Video", infoLabels )'''

            listitem.setProperty( 'playLabel', label )
            #listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/logos/' + i['image'] )
            listitem.setProperty( "fanart_image", fanart)
            self._add_context_menu( label, showUrl, 'show', listitem, False, True )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
    

    # --------------------------------------------------------------------------------------------
    # [ Start of scrappers -------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------
    
    def _getShowJSON(self, url):
        self._checkCookies()

        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}

        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=/channels/<channelName>/<showID>/<showName>
        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl='+url
        data = getRequest(url,urllib.urlencode(values),headers)

        sections = simplejson.loads(data)['body']['main']['sections']
        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(sections[1]['contentDownloadURL'].replace( " ", "+" ))
        return getRequest(url,urllib.urlencode(values),headers)        

        
    # Returns json of Channel labeled <label>
    def _getChannel(self, label):
        self._checkCookies()

        url = 'https://illicoweb.videotron.com/illicoservice/channels/user?localeLang=fr'
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)

        jsonList = simplejson.loads(data)['body']['main']
      
        for i in jsonList:
            if i['name'] == label:
                return i

                
    # Returns json of Seasons from a specific Show's URL
    # Can return a specific season number json if seasonNo arg is non-0
    def _getSeasons(self, url, seasonNo=0):
        self._checkCookies()
        
        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=/chaines/ChannelName
        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl=' + url
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        
        # get Channel sections to get URL for JSON shows
        data = getRequest(url,urllib.urlencode(values),headers)
        sections = simplejson.loads(data)['body']['main']['sections']

        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(sections[1]['contentDownloadURL'].replace( " ", "+" ))
        data = getRequest(url,urllib.urlencode(values),headers)
        
        listitems = []
        seasons = simplejson.loads(data)['body']
        if 'SeasonHierarchy' in seasons:
            seasons = simplejson.loads(data)['body']['SeasonHierarchy']['seasons']
            for i in seasons:
                # [body][SeasonHierarchy][seasons] seasons
                if seasonNo > 0:
                    if int(i['seasonNo']) == seasonNo:
                        # found specified season, return json
                        return i
                else: self._addSeasonsToShow(i,listitems)
                
        i = simplejson.loads(data)['body']['main']
        if not 'seasonNo' in i:
            # no season information, play show directly
            self._playEpisode(i['orderURI'])
            return
        
        # [body][main] seasons
        if seasonNo > 0:
            if int(i['seasonNo']) == seasonNo:
                # found specified season, return json
                return i
        else: self._addSeasonsToShow(i,listitems)
        
        if len(listitems) == 1 and seasonNo == 0:
            # only one season for this show, go straight to episode list
            return self._getEpisodes(data, str(i['seasonNo']))
 
        return listitems


    def _getShows(self, url):
        self._checkCookies()

        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl='+unquote_plus(url).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)

        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=/chaines/ChannelName
        addon_log("Getting fanart from URL: " + url)
        fanart = self._getChannelFanartImg(data)

        # Add LiveTV to top of show list
        i = simplejson.loads(data)['body']['main']['provider']
        livelist = []
        self._addLiveChannel(livelist, i, '%s?live="%s"', fanart) 
        
        data = self._getChannelShowsJSON(data)
        # No onDemand content? do nothing
        if data is None:
            return
        
        shows = simplejson.loads(data)['body']['main']['submenus']
        
        return shows, fanart, livelist
    
    def _getShow(self, url, label):
        self._checkCookies()

        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl='+unquote_plus(url).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)
        data = self._getChannelShowsJSON(data)
        
        '''url = 'http://illicoweb.videotron.com/illicoservice'+unquote_plus(url).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        
        data = getRequest(url,urllib.urlencode(values),headers)
        data = self._getChannelShowsJSON(data)
        # No onDemand content? do nothing
        if data is None:
            return'''
            
        shows = simplejson.loads(data)['body']['main']['submenus']   

        for i in shows:
            if 'submenus' in i:
                for show in i['submenus']:
                    if show['label'] == label:
                        return show
            else:
                if i['label'] == label:
                    return i
    
    def _getEpisodes(self, data, season):
        seasons = simplejson.loads(data)['body']['SeasonHierarchy']['seasons']
        listitems = []

        # [body][SeasonHierarchy][seasons] seasons
        for i in seasons:
            if(str(i['seasonNo']) == season):
                for ep in i['episodes']:
                    self._addEpisodes(ep, listitems)

        # [body][main] seasons
        i = simplejson.loads(data)['body']['main']
        if(str(i['seasonNo']) == season):
            for ep in i['episodes']:
                self._addEpisodes(ep, listitems)

        return listitems    

    def _getChannelShowsJSON(self, data):
        sections = simplejson.loads(data)['body']['main']['sections']
        onDemand = False
        for i in sections:
            if 'widgetType' in i:
                if i['widgetType'] == 'MENU':
                    onDemand = True
                    url = i['contentDownloadURL']
        if (onDemand == False):
            return
        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(url.replace( " ", "+" ))
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
            'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        return getRequest(url,urllib.urlencode(values),headers)
    
    def _getChannelFanartImg(self, data):
        sections = simplejson.loads(data)['body']['main']['sections']
        onDemand = False
        for i in sections:
            if 'widgetType' in i:
                if i['widgetType'] == 'PLAYER':
                    url = i['contentDownloadURL']

        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(url.replace( " ", "+" ))
        
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
            'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)
        img = simplejson.loads(data)['body']['main'][0]
        return 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/' + img['image']    
    
    # --------------------------------------------------------------------------------------------
    # [ End of scrappers -------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------
    
    def _playLive(self, url):
        self._checkCookies()
        url = 'https://illicoweb.videotron.com/illicoservice'+url
        addon_log("Live show at: %s" %url)
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)
        options = {'live': '1'}

        if not (self._checkEpisode(data,options)):
            addon_log("episode error")
    
    
    def _playEpisode(self, url):
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(url).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)

        if not (self._checkEpisode(data)):
            addon_log("episode error")
    
    def _checkEpisode(self, data, options={}):
        path = simplejson.loads(data)['body']['main']['mainToken']
        
        rtmp = path[:path.rfind('/')]
        playpath = ' Playpath=' + path[path.rfind('/')+1:]
        pageurl = ' pageUrl=' + unquote_plus(self.args.episode).replace( " ", "+" )
        swfurl = ' swfUrl=https://illicoweb.videotron.com/swf/vplayer_v1-3_215_prd.swf swfVfy=1'
        
        if 'live' in options.keys() and options['live']:
            live = ' live=1'
        else:
            live = ''

        final_url = rtmp+playpath+pageurl+swfurl+live
        
        item = xbmcgui.ListItem(xbmc.getInfoLabel( "ListItem.Property(playLabel)" ), '', xbmc.getInfoLabel( "ListItem.Property(playThumb)" ), xbmc.getInfoLabel( "ListItem.Property(playThumb)" ))

        import illicoPlayer as player
        try: player.playVideo( {'url':final_url,'item':item}, startoffset=0 )
        except: print_exc()
        
        return True 
        
    def _checkCookies(self):
        # Check if cookies have expired.
        cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=False)
        cookies = {}
        addon_log('These are the cookies we have in the cookie file:')
        for i in cookie_jar:
            cookies[i.name] = i.value
            addon_log('%s: %s' %(i.name, i.value))
        if cookies.has_key('iPlanetDirectoryPro'):
            addon_log('We have valid cookies')
            login = 'old'
        else:
            login = self._login()

        if not login:
            xbmcgui.Dialog().ok(ADDON_NAME, "Votre nom d'usager ou mot de passe est incorrect.\nAllez dans les options du plugin pour les mettre à jour.")
            exit(0)

        if login == 'old':
            # lets see if we get new cookies
            addon_log('old cookies: iPlanetDirectoryPro - %s' %(cookies['iPlanetDirectoryPro']))
            url = 'https://illicoweb.videotron.com/accueil'
            data = getRequest(url,None,None)
            addon_log('These are the cookies we have after https://illicoweb.videotron.com/accueil:')

        cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
        cookies = {}
        for i in cookie_jar:
            cookies[i.name] = i.value
            addon_log('%s: %s' %(i.name, i.value))

    def _login(self):
            addon_log('Login to get cookies!')

            if not username or not password:
                xbmcgui.Dialog().ok(ADDON_NAME, "Votre nom d'usager ou mot de passe est incorrect.\nAllez dans les options du plugin pour les mettre à jour.")
                exit(0)

            # Get the cookie first
            url = 'http://illicoweb.videotron.com/accueil'
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0'}
            login = getRequest(url,None,headers)

            # now authenticate
            url = 'https://illicoweb.videotron.com/illicoservice/authenticate?localLang=fr&password='+password+'&userId='+username
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'https://illicoweb.videotron.com/accueil',
                       'X-Requested-With' : 'XMLHttpRequest'}

            values = {}
            login = getRequest(url,urllib.urlencode(values),headers)

            cookie_jar.load(cookie_file, ignore_discard=False, ignore_expires=False)
            cookies = {}
            addon_log('These are the cookies we have received from authenticate.do:')
            for i in cookie_jar:
                cookies[i.name] = i.value
                addon_log('%s: %s' %(i.name, i.value))

            if cookies.has_key('iPlanetDirectoryPro'):
                return True
            else:
                return False

          
                
    def _add_directory_favourites( self ):
        OK = False
        listitems = []
        try:
            from xml.dom.minidom import parseString
            favourites = parseString( open( FAVOURITES_XML ).read()).getElementsByTagName( "favourite" )
            
            for favourite in favourites:
                label = favourite.getAttribute( "label" )
                category  = favourite.getAttribute( "category" )
                url = favourite.getAttribute( "url" )

                if category == 'channel':
                    i = self._getChannel(label)
                    if i:
                        self._addChannel(listitems, i, '%s?channel="%s"')

                elif category == 'live':
                    i = self._getChannel(label.replace(' - Live', ''))
                    if i:
                        i['name'] = label
                        i['link']['uri'] = i['orderURI']
                        self._addChannel(listitems, i, '%s?live="%s"')
                        
                elif category == 'show':
                    i = self._getShow(url, label)
                    if i:
                        self._addShowToChannel(i,listitems, "", url)
                        
                elif category == 'season':
                    # split the url to show url and seasonNo
                    seasonNo = int(url[url.rfind(',')+1:])
                    url = url[:url.rfind(',')]
                    i = self._getSeasons(url, seasonNo)
                    if i:
                        self._addSeasonsToShow(i, listitems, True)
                        
        except:
            print_exc()

        if listitems:
            addon_log("Creating directory items")
            OK = self._add_directory_items( listitems )
        self._set_content( OK, "movies", False )                
                
    def _add_directory_root( self ):
        self._checkCookies()

        url = 'https://illicoweb.videotron.com/illicoservice/channels/user?localeLang=fr'
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = getRequest(url,urllib.urlencode(values),headers)

        jsonList = simplejson.loads(data)['body']['main']
        listitems = []
        
        if os.path.exists( FAVOURITES_XML ):
            uri = sys.argv[ 0 ]
            item = ('-- Mes Favoris IllicoTV --', '', 'DefaultAddonScreensaver.png')
            listitem = xbmcgui.ListItem( *item )
            listitem.setProperty( "fanart_image", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/presse1.jpg')
            #self._add_context_menu_items( [], listitem, False )
            url = '%s?favoris="root"' %uri 
            listitems.append(( url, listitem, True ))
        
        OK = False
        for i in jsonList:
            self._addChannel(listitems, i, '%s?channel="%s"')

        if listitems:
            OK = self._add_directory_items( listitems )
        self._set_content( OK, "movies", False )

    '''
    ' Section de gestion des menus
    '''
    def _add_context_menu( self, label, url, category, listitem, watched=False, hidewatched=False ):
        try:
            c_items = [] #[ ( LangXBMC( 20351 ), "Action(Info)" ) ]

            #add to my favoris
            f = { 'label' : quote_plus(label.encode("utf8")), 'category' : category, 'url' : url}
            uri = '%s?addtofavourites="%s"' % ( sys.argv[ 0 ], urllib.urlencode(f) ) #favourite.encode('utf8').replace('"', '*' ))

            if self.args.favoris == "root":
                c_items += [ ( "Retirer de Mes Favoris", "RunPlugin(%s)" % uri.replace( "addto", "removefrom" ) ) ]
            else:
                c_items += [ ( "Ajouter à Mes Favoris", "RunPlugin(%s)" % uri ) ]
                
            if not hidewatched:
                if not watched:
                    i_label, action = 16103, "setwatched"
                else:
                    i_label, action = 16104, "setunwatched"
                if category == 'season':
                    all = 'True'
                else: all = 'False'
                uri = '%s?%s="%s*%s"&all=%s' % ( sys.argv[ 0 ], action, url, label, all )
                c_items += [ ( LangXBMC( i_label ), "RunPlugin(%s)" % uri ) ]

            self._add_context_menu_items( c_items, listitem )
        except:
            print_exc()

    def _add_context_menu_items( self, c_items, listitem, replaceItems=True ):
        c_items += [ ( LangXBMC( 1045 ), "Addon.OpenSettings(plugin.video.illicoweb)" ) ]

        listitem.addContextMenuItems( c_items, replaceItems )        

    '''
    ' Section de sort order
    ' e.g. 1, 2, 3, ... 10, 11, 12, ... 100, 101, 102, etc...
    '''
    def natsort_key(self, item):
        chunks = re.split('(\d+(?:\.\d+)?)', item[1].getLabel())
        for ii in range(len(chunks)):
            if chunks[ii] and chunks[ii][0] in '0123456789':
                if '.' in chunks[ii]: numtype = float
                else: numtype = int
                chunks[ii] = (0, numtype(chunks[ii]))
            else:
                chunks[ii] = (1, chunks[ii])
        return (chunks, item)

    def natural_sort(self, seq, reverseBool):
        sortlist = [item for item in seq]
        sortlist.sort(key=self.natsort_key, reverse = reverseBool)
        return sortlist
            
class Info:
    def __init__( self, *args, **kwargs ):
        # update dict with our formatted argv
        addon_log('__init__ addon received: %s' % sys.argv[ 2 ][ 1: ].replace( "&", ", " ).replace("%22",'"'))
        try: exec "self.__dict__.update(%s)" % ( sys.argv[ 2 ][ 1: ].replace( "&", ", " ).replace("%22",'"'), )
        except: print_exc()
        # update dict with custom kwargs
        self.__dict__.update( kwargs )

    def __getattr__( self, namespace ):
        return self[ namespace ]

    def __getitem__( self, namespace ):
        return self.get( namespace )

    def __setitem__( self, key, default="" ):
        self.__dict__[ key ] = default

    def get( self, key, default="" ):
        return self.__dict__.get( key, default )#.lower()

    def isempty( self ):
        return not bool( self.__dict__ )

    def IsTrue( self, key, default="false" ):
        return ( self.get( key, default ).lower() == "true" )

if ( __name__ == "__main__" ):
    Main()