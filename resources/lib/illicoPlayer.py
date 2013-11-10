import os
import sys
import xbmc
import xbmcgui

from traceback import print_exc
from xbmcaddon import Addon

addon             = Addon( "plugin.video.illicoweb" )

g_thumbnail = unicode( xbmc.getInfoImage( "ListItem.Thumb" ), "utf-8" )
#set our str watched
g_strwatched = xbmc.getInfoLabel( "ListItem.Property(strwatched)" )

def setWatched( listitem ):
    try:
        sys.modules[ 'resources.lib.illicoweb' ].setWatched( g_strwatched, refresh=True )
        listitem.setInfo( "video", { "playcount": 1 } )
    except: print_exc()

class XBMCPlayer( xbmc.Player ):
    """ Subclass of XBMC Player class.
        Overrides onplayback events, for custom actions.
        but onplayback not work with rtmp ! :(
    """
    def _play( self, url, listitem ):
        xbmc.log( "!!!!!!!!!!!!!!illicoPlayer: " + url, xbmc.LOGNOTICE )
        self.listitem = listitem
        self.play( url, self.listitem )

    def onPlayBackStarted( self ):
        xbmc.log( "!!!!!!!!!!illicoPlayer::onPlayBackStarted", xbmc.LOGNOTICE )
        exit(0)

    def onPlayBackPaused( self ):
        xbmc.log( "!!!!!!!!!!1illicoPlayer::onPlayPaused", xbmc.LOGNOTICE )
        exit(0)
        setWatched()

    def onPlayBackEnded( self ):
        xbmc.log( "!!!!!!!!!!1illicoPlayer::onPlayBackEnded", xbmc.LOGNOTICE )
        exit(0)
        setWatched()

    def onPlayBackStopped( self ):
        try: xbmc.log( "!!!!!!!!!!!!!Resume: %r" % self.getTime(), xbmc.LOGNOTICE )
        except: pass
        xbmc.log( "!!!!!illicoPlayer::onPlayBackStopped", xbmc.LOGNOTICE )
        exit(0)

class illicoPlayer( XBMCPlayer ):
    def __new__( cls, *args ):
        return XBMCPlayer.__new__( cls, *args )

def playVideo( details, startoffset=None, strwatched=None, listitem=None ):
    global g_strwatched
    if not g_strwatched and strwatched is not None:
        g_strwatched = strwatched

    setWatched( listitem )
        
    # play media
    player = illicoPlayer( xbmc.PLAYER_CORE_DVDPLAYER )
    player._play(details['url'],details['item'] )


if ( __name__ == "__main__" ):
    try:
        # get pid
        PID = sys.argv[ 1 ]
        playVideo( PID )
    except:
        print_exc()