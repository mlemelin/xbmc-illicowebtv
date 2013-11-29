# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

import sys
import xbmcplugin


class PluginView:
    def __init__( self ):
        pass

    def _add_directory_item( self, url, listitem, isFolder, totalItems ):
        """ addDirectoryItem(handle, url, listitem [,isFolder, totalItems])
            handle      : integer - handle the plugin was started with.
            url         : string - url of the entry. would be plugin:// for another virtual directory
            listitem    : ListItem - item to add.
            isFolder    : [opt] bool - True=folder / False=not a folder(default).
            totalItems  : [opt] integer - total number of items that will be passed.(used for progressbar)
        """
        return xbmcplugin.addDirectoryItem( int( sys.argv[ 1 ] ), url, listitem, isFolder, totalItems )
    
    def _add_directory_items( self, listitems ):
        """ addDirectoryItems(handle, items [,totalItems])
            handle      : integer - handle the plugin was started with.
            items       : List - list of (url, listitem[, isFolder]) as a tuple to add.
            totalItems  : [opt] integer - total number of items that will be passed.(used for progressbar)
        """
        return xbmcplugin.addDirectoryItems( int( sys.argv[ 1 ] ), listitems, len( listitems ) )

    def _set_content( self, succeeded, content, sort=True ):
        if ( succeeded ):
            xbmcplugin.setContent( int( sys.argv[ 1 ] ), content )
        if sort:
            self._add_sort_methods( succeeded )
        else:
            self._end_of_directory( succeeded )

    def _add_sort_methods( self, succeeded ):
        if ( succeeded ):
            xbmcplugin.addSortMethod( int( sys.argv[ 1 ] ), xbmcplugin.SORT_METHOD_UNSORTED )
            xbmcplugin.addSortMethod( int( sys.argv[ 1 ] ), xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE )
            xbmcplugin.addSortMethod( int( sys.argv[ 1 ] ), xbmcplugin.SORT_METHOD_EPISODE )
            xbmcplugin.addSortMethod( int( sys.argv[ 1 ] ), xbmcplugin.SORT_METHOD_VIDEO_YEAR )
            xbmcplugin.addSortMethod( int( sys.argv[ 1 ] ), xbmcplugin.SORT_METHOD_GENRE )
            xbmcplugin.addSortMethod( int( sys.argv[ 1 ] ), xbmcplugin.SORT_METHOD_MPAA_RATING )
        self._end_of_directory( succeeded )

    def _end_of_directory( self, succeeded ):
        xbmcplugin.endOfDirectory( int( sys.argv[ 1 ] ), succeeded )
