import os
import sys
import xbmc
import xbmcgui
import time

from traceback import print_exc
from xbmcaddon import Addon

ADDON = Addon( "plugin.video.illicoweb" )
ADDON_CACHE = xbmc.translatePath( ADDON.getAddonInfo( "profile" ) )
DEBUG = ADDON.getSetting('debug')

def addon_log(string):
    #if DEBUG == 'true':
    xbmc.log("[Illico-Service]: %s" %(string))
    
def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    if minutes > 60:
        hours, minutes = divmod(minutes, 60)
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    else:
        return "%02d:%02d" % (minutes, seconds)

def getWatched():
    watched = {}
    try:
        watched_db = os.path.join( ADDON_CACHE, "watched.db" )
        if os.path.exists( watched_db ):
            watched = eval( open( watched_db ).read() )
    except:
        print_exc()
    return watched    
    
def setWatched(strwatched, remove=False, refresh=True):
    if not strwatched: return
    
    watched = getWatched()
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
        addon_log("Refreshing directory after setting watched status")
        xbmc.executebuiltin( 'Container.Refresh' )

class Service(xbmc.Player):
    """
    An XBMC Service that monitors playback from this addon to save and record resume positions
    """
    
    # Static constants for resume db and lockfile paths
    RESUME_FILE = None
    
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self, *args, **kwargs)
        self.reset()

        self.RESUME_FILE    = os.path.join(ADDON_CACHE, 'illico_resume.db')
        self.resume, self.dates_added = self.load_resume_file()
        addon_log('Resume file: %s' % self.RESUME_FILE)
        
        addon_log('Starting...')


    def reset(self):
        addon_log('Resetting...')
        win = xbmcgui.Window(10000)
        win.clearProperty('illico.playing.title')
        win.clearProperty('illico.playing.pid')
        win.clearProperty('illico.playing.live')
        win.clearProperty('illico.playing.watched')
        
        self.paused = False
        self.live = False
        self.pid = ""
        self._lastPos=0
        self._sought = False
        self.tracking = False
        self.watched = ""

        
    def check(self):
        win = xbmcgui.Window(10000)
        if win.getProperty('illico.playing.title'):
            return True
        else:
            return False

           
    def onPlayBackStarted( self ):
        # Will be called when xbmc starts playing the stream
        
        self.tracking = self.check()
        if (self.tracking):
            addon_log('Tracking progress...')
            win = xbmcgui.Window(10000)
            self.title = win.getProperty('illico.playing.title')
            self.pid = win.getProperty('illico.playing.pid')
            self.live = win.getProperty('illico.playing.live')
            self.watched = win.getProperty('illico.playing.watched')
            self._totalTime = self.getTotalTime()
            
            addon_log( "Begin playback of pid %s" % (self.pid) )
            
            if ADDON.getSetting('resume') == 'true':
                if not self.live == 'true' and self.pid in self.resume.keys():
                    bookmark = self.resume[self.pid]
                    if not (self._sought and (bookmark - 30 > 0)):
                        question = 'Reprendre la position %s?' % (format_time(bookmark))
                        restart = xbmcgui.Dialog()
                        restart = restart.yesno(self.title, '', question, '', 'Continuer', 'Recommencer' )
                        if not restart: self.seekTime(bookmark)
                        self._sought = True

    
    def onPlayBackPaused( self ):
        addon_log( 'Playback paused...' )
    
    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing the stream
        addon_log( 'Playback ended...' )
        self.onPlayBackStopped()
    
    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing the stream
        addon_log( 'Playback stopped...')
        if self.tracking and not self.live == 'true':
            # Playback threshold is 80% of totaltime
            playedTime = int(self._lastPos)
            min_watched_percent = .8
            percent = int((playedTime / self._totalTime) * 100)
            pTime = format_time(playedTime)
            tTime = format_time(self._totalTime)
            addon_log('%s played of %s total = %s%%' % (pTime, tTime, percent))
            if playedTime == 0 and self._totalTime == 999999:
                raise RuntimeError('XBMC silently failed to start playback')
            elif ((playedTime / self._totalTime) > min_watched_percent):
                addon_log('Threshold met. Marking item as watched')
                setWatched(self.watched)
                self.delete_resume_point(self.pid)
            else:
                addon_log('Threshold not met. Saving bookmark')
                self.save_resume_point( self._lastPos )

        self.reset()
    
    
    def save_resume_point( self, resume_point ):
        """
        Updates the current resume point for the currently playing pid to resume_point, and commits the result to the resume db file
        """
        self.resume[self.pid] = resume_point
        self.dates_added[self.pid] = time.time()
        addon_log('Saving resume point (pid %s, seekTime %fs, dateAdded %d) to resume file' % (self.pid, self.resume[self.pid], self.dates_added[self.pid]))
        self.save_resume_file(self.resume, self.dates_added)

    def load_resume_file(self):
        """
        Loads and parses the resume file, and returns a dictionary mapping pid -> resume_point
        Resume file format is three columns, separated by a single space, with platform dependent newlines
        First column is pid (string), second column is resume point (float), third column is date added
        If date added is more than thirty days ago, the pid entry will be ignored for cleanup
        """
        # Load resume file
        resume = {}
        dates_added = {}
        if os.path.isfile(self.RESUME_FILE):
            addon_log('Loading resume file: %s' % (self.RESUME_FILE))
            resume_fh = open(self.RESUME_FILE, 'rU')
            try:
                resume_str = resume_fh.read()
            finally:
                resume_fh.close()
            tokens = resume_str.split()
            # Three columns, pid, seekTime (which is a float) and date added (which is an integer, datetime in seconds), per line
            pids = tokens[0::3]
            seekTimes = [float(seekTime) for seekTime in tokens[1::3]]
            datesAdded = [int(dateAdded) for dateAdded in tokens[2::3]]
            pid_to_resume_point_map = []
            pid_to_date_added_map = []
            for i in range(len(pids)):
                # if row was added less than days_to_keep days ago, add it to valid_mappings
                try: days_to_keep = int(__addon__.getSetting('resume_days_to_keep'))
                except: days_to_keep = 40
                if datesAdded[i] > time.time() - 60*60*24*days_to_keep:
                    pid_to_resume_point_map.append( (pids[i], seekTimes[i]) )
                    pid_to_date_added_map.append( (pids[i], datesAdded[i]) )
            resume = dict(pid_to_resume_point_map)
            dates_added = dict(pid_to_date_added_map)
            addon_log('Found %d resume entries' % (len(resume.keys())))
        return resume, dates_added

    def delete_resume_point(self, pid_to_delete):
        addon_log('Deleting resume point for pid %s' % pid_to_delete)
        if pid_to_delete in self.resume.keys():
            addon_log('Found resume point for pid %s, deleting...' % pid_to_delete)
            del self.resume[pid_to_delete]
            del self.dates_added[pid_to_delete]
        self.save_resume_file(self.resume, self.dates_added)
            
    def save_resume_file(self, resume, dates_added):
        """
        Saves the current resume dictionary to disk. See load_resume_file for file format
        """
        str = ""
        addon_log('Saving %d entries to %s' % (len(resume.keys()), self.RESUME_FILE))
        resume_fh = open(self.RESUME_FILE, 'w')
        try:
            for pid, seekTime in resume.items():
                str += "%s %f %d\n" % (pid, seekTime, dates_added[pid])
            resume_fh.write(str)
        finally:
            resume_fh.close()



monitor = Service()
while not xbmc.abortRequested:
    while monitor.tracking and monitor.isPlayingVideo():
        monitor._lastPos = monitor.getTime()
        xbmc.sleep(1000)
    xbmc.sleep(1000)
addon_log('Service: shutting down...')
        