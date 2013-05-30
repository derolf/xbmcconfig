# (C) dero, based on jhh's initial XBMC-4tr "simple" client

import urllib,urllib2,re,xbmcplugin,xbmcgui, xbmcaddon
import string,re,sys,socket,os, xml.dom.minidom, operator
import json, sqlite3, datetime, threading, time
from thread import start_new_thread
from threading import Thread
from Queue import Queue
from shared import *

# globals
settings= 	xbmcaddon.Addon(id='addon.video.4TRBrowser')
filename_re= 	re.compile( settings.getSetting('fn_re' ) )
filename_sub=	settings.getSetting('fn_sub')
date_fmt=	settings.getSetting('dt_fmt')
date_label=	settings.getSetting('dt_label').lower() == "true"

# some strings
SGroupBySchedule= 	 settings.getLocalizedString( 33505 ) 
SGroupByProgramTitle=	 settings.getLocalizedString( 33506 ) 
SListProgramTitleLatest= settings.getLocalizedString( 33507 ) 
SSchemaChanged=		 settings.getLocalizedString( 33508 ) 
SErrorRPC=		 settings.getLocalizedString( 33509 ) 
SListingChanged=	 settings.getLocalizedString( 33510 ) 
SLoading=		 "Lade Eintrag %s von %s"

# main
def main():
    try: os.mkdir( cachePath )
    except: pass
    
    checkSchema()
  
    params= None
    cmd=    None

    print sys.argv

    args= sys.argv[2]
    if len(args) >= 2:
      args=   json.loads(urllib.unquote_plus(args[1:]))
      cmd=    args[ "cmd" ]
      params= args[ "params" ]

    print "Cmd   : "+str(cmd)
    print "Params: "+str(params)
    
    if cmd == None:
      addDirectoryItem( SGroupBySchedule, "", { "":"" }, "", "", "GroupBySchedule", True, 3 )
      addDirectoryItem( SGroupByProgramTitle, "", { "":"" }, "", "", "GroupByProgramTitle", True, 3 )
      addDirectoryItem( SListProgramTitleLatest, "", { "":"" }, "", "", "ListProgramTitleLatest", True, 3 )
      xbmc.executebuiltin("Container.SetViewMode(56)")

    elif cmd == "ListProgramTitleLatest":
      try: ListProgramTitleLatest()
      except: pass
      xbmc.executebuiltin("Container.SetViewMode(52)")       

    elif cmd == "GroupByProgramTitle":
      try: GroupByProgramTitle()
      except: pass
      xbmc.executebuiltin("Container.SetViewMode(52)")        
      
    elif cmd == "GroupBySchedule":
      try: GroupBySchedule()
      except: pass
      xbmc.executebuiltin("Container.SetViewMode(52)")        
	
    elif cmd =="RecordingsForProgramTitle":
      try: RecordingsForProgramTitle( params )
      except: pass
      xbmc.executebuiltin("Container.SetViewMode(52)")
      
    elif cmd =="RecordingsForScheduleId":
      try: RecordingsForScheduleId(  params )
      except: pass
      xbmc.executebuiltin("Container.SetViewMode(52)")
      
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
    print "DONE"
  
# push notification
def notification(message,time):
    xbmc.executebuiltin("Notification(4TR Browser," + message.encode( "UTF-8" ) + "," + str(time) + ")");

lastProgress= None
def progress(cur,total):
    global lastProgress
    now= time.time()
    if lastProgress is not None and ( now - lastProgress ) < 1: return
    lastProgress= now    
    notification( SLoading % ( cur, total ), 1000 )

def addDirectoryItem( label, label2, info, iconimage, params, cmd, fold, total ):
    u=   sys.argv[0] + "?" + urllib.quote_plus(json.dumps( { "cmd" : cmd, "params" : params } ) )
    liz= xbmcgui.ListItem( label, label2, iconImage=iconimage, thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels=info )
    xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=fold, totalItems= total )
    
def addDirectoryItemURL( label, label2, info, iconimage, u, total ):
    liz= xbmcgui.ListItem( label, label2, iconImage=iconimage, thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels=info )
    xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False, totalItems= total )

def getThumbnailURL(id, width):
    path= cachePath + "/thumbs/%sx%d.jpg" % ( id, width )
    if not os.path.exists(path) or os.path.getsize(path) == 0: return None
    return path
    
def getLatestCachedThumbnailURL( recs, width ):
    if lst is None: return None
    for r in recs:
      url= getThumbnailURL( r[ "RecordingId" ], width )
      if url is not None: return url
    return None
  
# pattern to parse dotnet JSON dates
date_re= re.compile(r"^/Date\((.*)\+(..)(..)\)/$")    
 
# format dotnet JSON date
def date( s ):
    mat= date_re.match( s )
    ts= int( mat.group( 1 ) ) / 1000
    h= int( mat.group( 2 ) )
    m= int( mat.group( 3 ) )
    tm= datetime.datetime.utcfromtimestamp(ts + h * 3600 + m * 60 )
    return tm.strftime( date_fmt )
    
def buildPlaybackURL(filename):
    filename= filename.replace( "\\", "/" )
    return filename_re.sub( filename_sub, filename )
  
def addRecording( d, total, includeTitle ):
    subTitle= d[ 'SubTitle' ]
    title= d[ "Title" ]
      
    if includeTitle:
      label= title
      if subTitle != "":
	label= label + ": " + subTitle
    else:
      if subTitle != "":
	label= subTitle
      else:
	label= title

    tn= getThumbnailURL( d[ "RecordingId" ], 512 ) or ""
    plot= d[ "Description" ]
    tagline= date( d[ "ProgramStartTime" ] )
	
    if d[ 'EpisodeNumberDisplay' ] != '':
      label= label + " (" + d[ 'EpisodeNumberDisplay' ] + ")"
      tagline= tagline + " - " + d[ 'EpisodeNumberDisplay' ]
    if date_label: label= label + " - " + date( d[ "ProgramStartTime" ] )
    info=  { "Plot": plot, "Tagline": tagline, "Title": subTitle }
    
    addDirectoryItemURL( label, "", info, tn, buildPlaybackURL( d[ "RecordingFileName" ] ), total )
      
    
def loadGroupByAndRefreshThread( group ):
    li = sorted(li, key=operator.itemgetter("LatestProgramStartTime"), reverse = True)
    
def RecordingsForScheduleId(params):
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )
    li= GET( "Group", "GroupBySchedule", params[ "ID" ] ).values()
    li= sorted(li, key=operator.itemgetter("ProgramStartTime"), reverse = True)
    idx= 0
    for l in li:
      idx= idx + 1
      progress( idx, len( li ) )
      addRecording( l, len(li), True )
      
def RecordingsForProgramTitle(params):
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )
    li= GET( "Group", "GroupByProgramTitle", params[ "ID" ] ).values()
    li= sorted(li, key=operator.itemgetter("ProgramStartTime"), reverse = True)
    idx= 0
    for l in li:
      idx= idx + 1
      progress( idx, len( li ) )
      addRecording( l, len(li), True )
      
def GroupBySchedule():
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )
    li= GET( "Group", "GroupBySchedule" ).values()
    li= sorted(li, key=operator.itemgetter("LatestProgramStartTime"), reverse = True)
    idx= 0
    for m in li:
      idx= idx + 1
      progress( idx, len( li ) )
    	
      label= m[ 'ScheduleName' ] + " (" + str( m[ 'RecordingsCount' ] ) +")"
      if date_label: label= label + " - " + date( m[ "LatestProgramStartTime" ] )
      info= { "Title": m[ 'ScheduleName' ], "Tagline": date( m[ "LatestProgramStartTime" ] ) }
      params= { "ID" : m[ "ID" ] }
      tn= "" # getLatestCachedThumbnailURL( getCachedLatestRecordings( "ScheduleId", m[ "ScheduleId" ] ), 512 )
      tn= tn if tn else ""
      addDirectoryItem( label, "", info, tn, params, 'RecordingsForScheduleId', True, len(li) )
      
def GroupByProgramTitle():
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )
    li= GET( "Group", "GroupByProgramTitle" ).values()
    li= sorted(li, key=operator.itemgetter("LatestProgramStartTime"), reverse = True)
    idx= 0
    for m in li:
      idx= idx + 1
      progress( idx, len( li ) )
  
      label= m[ 'ProgramTitle' ] + " (" + str( m[ 'RecordingsCount' ] ) +")"
      if date_label: label= label + " - " + date( m[ "LatestProgramStartTime" ] )
      info= { "Title": m[ 'ProgramTitle' ], "Tagline": date( m[ "LatestProgramStartTime" ] ) }
      params= { "ID" : m[ "ID" ] }
      tn= "" # getLatestCachedThumbnailURL( getCachedLatestRecordings( "ProgramTitle", m[ "ProgramTitle" ] ), 512 )
      tn= tn if tn else ""
      addDirectoryItem( label, "", info, tn, params, 'RecordingsForProgramTitle', True, len(li) )   
      
def ListProgramTitleLatest():
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )  

    li= GET( "Group", "GroupByProgramTitle" ).values()
    li= sorted(li, key=operator.itemgetter("LatestProgramStartTime"), reverse = True)
    idx= 0
    for l in li:
      idx= idx + 1
      progress( idx, len( li ) )
      
      lis= GET( "Group", "GroupByProgramTitle", l[ "ID" ] ).values()
      lis= sorted(lis, key=operator.itemgetter("ProgramStartTime"), reverse = True)
      if len( lis ) > 0:
	addRecording( lis[0], len(li), True )
	
# call main!
main()
