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
import StorageServer

from urllib import quote_plus, unquote_plus
from traceback import print_exc
from traceback import print_exc
from BeautifulSoup import BeautifulSoup
import HTMLParser


addon = xbmcaddon.Addon(id='plugin.video.illicoweb')
addon_version = "1"
username = addon.getSetting( "username" )
password = addon.getSetting( "password" )
profile = xbmc.translatePath(addon.getAddonInfo('profile'))
home = xbmc.translatePath(addon.getAddonInfo('path'))
language = addon.getLocalizedString
icon = os.path.join(home, 'icon.png')
cookie_file = os.path.join(profile, 'cookie_file')
cookie_jar = cookielib.LWPCookieJar(cookie_file)
cache = StorageServer.StorageServer("illicoweb", 2)
debug = addon.getSetting('debug')
if debug == 'true':
    cache.dbg = True


ADDON_NAME        = addon.getAddonInfo( "name" )

def addon_log(string):
    if debug == 'true':
        xbmc.log("[Illicoweb-%s]: %s" %(addon_version, string))

def getRequest(url, data=None, headers=None):
    if not xbmcvfs.exists(cookie_file):
        addon_log('Creating cookie_file!')
        cookie_jar.save()
    if headers is None:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'http://www.illicoweb.videotron.com'}
    cookie_jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
    urllib2.install_opener(opener)
    try:
        req = urllib2.Request(url,data,headers)
        response = urllib2.urlopen(req)
        data = response.read()
        cookie_jar.save(cookie_file, ignore_discard=True, ignore_expires=False)
        response.close()
        if debug == "true":
            addon_log("getRequest : %s" %url)
            addon_log(response.info())
            if response.geturl() != url:
                addon_log('Redirect URL: %s' %response.geturl())
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

if re.search( '(GetCarrousel|"carrousel")', sys.argv[ 2 ] ):
    from GuiView import GuiView as viewtype
else:
    from PluginView import PluginView as viewtype

class Main( viewtype ):
    def __init__( self ):
        viewtype.__init__( self )
        self.args = Info()
        #self.watched = getWatched()


        if self.args.isempty():
            self._login()
            self._add_directory_root()

        elif self.args.live:
            self._checkCookies()
            url = 'http://illicoweb.videotron.com/'+unquote_plus(self.args.live).replace( " ", "+" )
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'http://illicoweb.videotron.com/illicoweb/toutes-les-chaines/toutes'}
            values = {}
            data = getRequest(url,urllib.urlencode(values),headers)
            options = {'live': '1'}

            if not (self._checkEpisode(data,options)):
                addon_log("episode error")

        elif self.args.episode:
            self._checkCookies()
            url = 'http://illicoweb.videotron.com/'+unquote_plus(self.args.episode).replace( " ", "+" )
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'http://illicoweb.videotron.com/illicoweb/toutes-les-chaines/toutes'}
            values = {}
            data = getRequest(url,urllib.urlencode(values),headers)

            if not (self._checkEpisode(data)):
                addon_log("episode error")


        elif self.args.channel:
            url = 'http://illicoweb.videotron.com'+unquote_plus(self.args.channel).replace( " ", "+" )

            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'http://illicoweb.videotron.com/illicoweb/toutes-les-chaines/toutes'}
            values = {}
            data = getRequest(url,urllib.urlencode(values),headers)

            soup = BeautifulSoup(data)
            addon_log(soup.find('ul', {'id': 'left-menu'}))
            logo = soup.find("div", {'id':'chaine-logo'}).img['src']
            listitems = []
            for i in soup.find('ul', {'id': 'left-menu'}).findNext("ul",{},).findAll("li",{},recursive=False):
                if(i.a):
                    showUrl = i.a['href']
                    label = HTMLParser.HTMLParser().unescape(i.a.getText())
                    addon_log(showUrl)

                    OK = False                
                    try:
                        uri = sys.argv[ 0 ]
                        item = ( label,     '')
                        url = '%s?show="%s"' %( uri, showUrl  )
                        listitem = xbmcgui.ListItem( *item )
                        listitems.append( ( url, listitem, True ) )
                    except:
                        print_exc()

            if listitems:
                OK = self._add_directory_items( listitems )
            self._set_content( OK, "movies", False )

        elif self.args.show:

            self._checkCookies()

            url = 'http://illicoweb.videotron.com'+unquote_plus(self.args.show).replace( " ", "+" )
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'http://illicoweb.videotron.com/illicoweb/toutes-les-chaines/toutes'}
            values = {}
            data = getRequest(url,urllib.urlencode(values),headers)

            if not self._checkEpisode(data):

                soup = BeautifulSoup(data)
                listitems = []
                seasons = soup.find('ul', {'class': 'group'}).findAll("li")
                addon_log(seasons) 
                for i in seasons:
                    if(i.a):
                        label = 'Saison ' + HTMLParser.HTMLParser().unescape(i.a.getText())
                        seasonUrl = self.args.show + '#' + i.a.getText()
                        OK = False                
                        try:
                            uri = sys.argv[ 0 ]
                            item = ( label,     '', 'DefaultAddonSubtitles.png')
                            url = '%s?season="%s"' %( uri, seasonUrl  )
                            listitem = xbmcgui.ListItem( *item )
                            listitems.append( ( url, listitem, True ) )
                        except:
                            print_exc()

                if listitems:
                    listitems = sorted(listitems,reverse=True)
                    OK = self._add_directory_items( listitems )
                self._set_content( OK, "movies", False )

        elif self.args.season:
            urlParts = unquote_plus(self.args.season).replace( " ", "+" ).split("#")

            url = 'http://illicoweb.videotron.com'+urlParts[0]
            season = urlParts[1]
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'http://illicoweb.videotron.com/illicoweb/toutes-les-chaines/toutes'}
            values = {}
            data = getRequest(url,urllib.urlencode(values),headers)

            if not self._checkEpisode(data):

                soup = BeautifulSoup(data)

                listitems = []
                episodes = soup.find('div', {'id': 'content_'+season}).findAll("ul",{'class':'season-content'},recursive=False)
                for i in episodes:
                    label = HTMLParser.HTMLParser().unescape(i.a.getText())
                    episodeUrl = i.a['href']
                    OK = False                
                    try:
                        uri = sys.argv[ 0 ]
                        item = ( label,     '', 'DefaultAddonSubtitles.png')
                        url = '%s?episode="%s"' %( uri, episodeUrl  )
                        listitem = xbmcgui.ListItem( *item )
                        listitems.append( ( url, listitem, True ) )
                    except:
                        print_exc()

                if listitems:
                    listitems = sorted(listitems,reverse=True)
                    OK = self._add_directory_items( listitems )
                self._set_content( OK, "movies", False )

        elif self.args.category == "direct":

            self._checkCookies()

            url = 'http://illicoweb.videotron.com/illicoweb/displayChannelPage!execute.action?currentPage=mesChaines&lang=fr&filterType=EnDirect'
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'http://illicoweb.videotron.com/illicoweb/toutes-les-chaines/toutes'}
            values = {}
            data = getRequest(url,urllib.urlencode(values),headers)

            soup = BeautifulSoup(data)
            listitems = []
            for i in soup.findAll('span', {'class': 'title channel-title'}):
                episodeUrl = i.parent['href']
                img = ''.join(i.parent.img['src'].splitlines()).replace("\t","")
                OK = False                
                try:
                    uri = sys.argv[ 0 ]
                    item = ( HTMLParser.HTMLParser().unescape(i.strong.getText()), '', img)
                    url = '%s?live="%s"' %( uri, episodeUrl  )
                    listitem = xbmcgui.ListItem( *item )
                    listitems.append( ( url, listitem, True ) )
                except:
                    print_exc()

            if listitems:
                OK = self._add_directory_items( listitems )
            self._set_content( OK, "movies", False )

        elif self.args.category == "ondemand":

            self._checkCookies()

            url = 'http://illicoweb.videotron.com/illicoweb/displayChannelPage!execute.action?currentPage=mesChaines&lang=fr&filterType=Toutes'
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'http://illicoweb.videotron.com/illicoweb/toutes-les-chaines/toutes'}
            values = {}
            data = getRequest(url,urllib.urlencode(values),headers)

            soup = BeautifulSoup(data)
            #liste = soup.find_all("span")
            listitems = []

            for i in soup.findAll('span', {'class': 'title channel-title'}):
                episodeUrl = i.parent['href']
                img = ''.join(i.parent.img['src'].splitlines()).replace("\t","")
                OK = False                
                try:
                    uri = sys.argv[ 0 ]
                    item = ( HTMLParser.HTMLParser().unescape(i.strong.getText()),     '', img)
                    url = '%s?channel="%s"' %( uri, episodeUrl  )
                    listitem = xbmcgui.ListItem( *item )
                    listitems.append( ( url, listitem, True ) )
                except:
                    print_exc()

            if listitems:
                OK = self._add_directory_items( listitems )
            self._set_content( OK, "movies", False )
    
    def _checkEpisode(self, data, options={}):

        varList = re.findall("flashvars:\{(.*?)\}", data, re.S)
        if(len(varList) == 0):

            return False

        else:
            varList = varList[0]
            varList = varList.replace("\n","").replace("\r","").replace("\t","")
        
            rtmp = re.findall("mediaURL: \"(.*?)\"",varList)[0]
            playpath = ' Playpath=' + re.findall("mediaStream: \"(.*?)\"",varList)[0]
            pageurl = ' pageUrl=' + self.args.episode
            swfurl = ' swfUrl=http://static-illicoweb.videotron.com/illicoweb/static/webtv/assets/swf/01/vplayer_v1-1_213_prd.swf swfVfy=1'
            addon_log(options)
            if 'live' in options.keys() and options['live']:
                live = ' live=1'
            else:
                live = ''

            final_url = rtmp+playpath+pageurl+swfurl+live

            item = xbmcgui.ListItem('test')

            #xbmc.Player(xbmc.PLAYER_CORE_AUTO).play(final_url, item) 
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
            url = 'http://illicoweb.videotron.com/illicoweb/accueil'
            data = getRequest(url,None,None)
            addon_log('These are the cookies we have after http://illicoweb.videotron.com/illicoweb/accueil:')

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
            url = 'http://illicoweb.videotron.com/illicoweb/accueil'
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0'}
            login = getRequest(url,None,headers)

            # now authenticate
            url = 'http://illicoweb.videotron.com/illicoweb/overlayLogOn.action'
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                       'Referer' : 'http://illicoweb.videotron.com/illicoweb/accueil',
                       'X-Requested-With' : 'XMLHttpRequest'}
            values = {'episodeContentId' : '0',
                      'seasonContentId' : '0',
                      'tree' : '',
                      'forceRedirect' : 'reload',
                      'userName' : username,
                      'password' : password}
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

    def _add_directory_root( self ):
        OK = False
        listitems = []
        try:
            uri = sys.argv[ 0 ]

            items = [
                ( ( uri, 'direct'   ), ( 'En direct',     '', 'DefaultAddonSubtitles.png') ),
                ( ( uri, 'ondemand' ), ( 'Sur demande',   '', 'DefaultAddonSubtitles.png') ),
            ]
            
            for uri, item in items:
                listitem = xbmcgui.ListItem( *item )
                #listitem.setProperty( "fanart_image", fanart )
                #self._add_context_menu_items( [], listitem )
                url = '%s?category="%s"' % uri
                listitems.append( ( url, listitem, True ) )
        except:
            print_exc()

        if listitems:
            OK = self._add_directory_items( listitems )
        self._set_content( OK, "movies", False )

class Info:
    def __init__( self, *args, **kwargs ):
        # update dict with our formatted argv
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