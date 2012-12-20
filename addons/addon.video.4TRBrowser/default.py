# (C) dero, based on jhh's initial XBMC-4tr "simple" client

import urllib,urllib2,re,xbmcplugin,xbmcgui, xbmcaddon
import string,re,sys,socket,os, xml.dom.minidom, operator
import json, sqlite3, datetime, threading
from thread import start_new_thread
from threading import Thread
from Queue import Queue

# globals
settings= 	xbmcaddon.Addon(id='addon.video.4TRBrowser')
ip_addr= 	settings.getSetting('ip_addr')
ip_port= 	settings.getSetting('ip_port')
webaddress= 	"http://" + ip_addr + ":" + ip_port
cachePath= 	os.getcwd() + "/cache/"
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
SLoadingItems=		 "Lade Eintrag %s von %s"

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

# poor man's SQLLite singleton serializer...
class CacheDB():
    lock= threading.Lock()

    def execute(self, req, arg=None):
	self.lock.acquire()
	try:
	  db= sqlite3.connect( cachePath + "cache.db")
	  try:
	    dbc= db.cursor()
	    dbc.execute( req, arg or tuple())
	    res= []
	    for rec in dbc:
	      res.append(rec)
	    db.commit()
	    return res
	  finally:
	    db.close()        
	finally:
	  self.lock.release()
	  
    def selectFirst(self, req, arg=None):
        res= self.execute( req, arg or tuple())
        if len( res ) == 0: return None
        return res[0]

cacheDB= CacheDB()
        
def cachedbc():
    return cacheDB

# check/recreate cache schema
def checkSchema():
  v= cachedbc().selectFirst( "SELECT * FROM sqlite_master WHERE type= ? AND name = ?", ( "table", "General", ) )
  if v != None:
    v= cachedbc().selectFirst("SELECT Details FROM General WHERE Key = ?", ( "Version", ) )
  if v == None or int(v[0]) < 2:
    if v != None: notification( SSchemaChanged, 10000 )
    cachedbc().execute("DROP TABLE IF EXISTS RecordingById" )
    cachedbc().execute("DROP TABLE IF EXISTS RecordingGroups")
    cachedbc().execute("DROP TABLE IF EXISTS General")
    cachedbc().execute("CREATE TABLE RecordingById ( RecordingId text PRIMARY KEY, ProgramTitle text, ScheduleId text, Details text)")
    cachedbc().execute("CREATE TABLE RecordingGroups (Key text, Value text, Details text, PRIMARY KEY( Key, Value ) )")
    cachedbc().execute("CREATE TABLE General (Key text PRIMARY KEY, Details text)")
    cachedbc().execute("INSERT INTO General VALUES( ?, ? )", ( "Version", "2", ) )

# call 4TR    
def RPC(endpoint, post):
    try:
      url=      webaddress + '/ForTheRecord/' + endpoint
      print "Calling FTR: " + url
      WebSock=  urllib2.urlopen(url, post)
      content=  WebSock.read()
      headers=  WebSock.headers
      WebSock.close()
      return { "content": content, "headers" : headers }
    except:
      notification( SErrorRPC, 5000 )
      raise    
    
def XRPC(endpoint, post):
    try:
      url=      endpoint
      print "Calling: " + url
      WebSock=  urllib2.urlopen(url, post)
      content=  WebSock.read()
      headers=  WebSock.headers
      WebSock.close()
      return { "content": content, "headers" : headers }
    except:
      notification( SErrorRPC, 5000 )
      raise    
    
def JSONRPC(endpoint, post):
    res= RPC( endpoint, post )
    content=  res[ "content" ]
    charset=  res[ "headers" ]['content-type'].split('charset=')[-1]    
    return json.loads( content, charset )
    
def JSONXRPC(endpoint, post):
    res= XRPC( endpoint, post )
    content=  res[ "content" ]
    charset=  res[ "headers" ]['content-type'].split('charset=')[-1]    
    return json.loads( content, charset )
    
def addDirectoryItem( label, label2, info, iconimage, params, cmd, fold, total ):
    u=   sys.argv[0] + "?" + urllib.quote_plus(json.dumps( { "cmd" : cmd, "params" : params } ) )
    liz= xbmcgui.ListItem( label, label2, iconImage=iconimage, thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels=info )
    xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=fold, totalItems= total )
    
def addDirectoryItemURL( label, label2, info, iconimage, u, total ):
    liz= xbmcgui.ListItem( label, label2, iconImage=iconimage, thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels=info )
    xbmcplugin.addDirectoryItem( handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False, totalItems= total )
    
def getRecordingById(id):
    cached= cachedbc().selectFirst("SELECT Details FROM RecordingById WHERE RecordingId=?", ( id, ) )
    if cached != None:
      return json.loads( cached[0] )
    
    d= JSONRPC( 'Control/RecordingById/' + id, urllib.urlencode('') )
    cachedbc().execute("INSERT INTO RecordingById VALUES( ?, ?, ?, ? )", ( id, d[ "Title" ], d[ "ScheduleId" ], json.dumps( d ), ) );
    return d
    
def getRecordingGroup(uri, key,value,latestProgramStartTime, recordingsCount):
    cached= cachedbc().selectFirst("SELECT Details FROM RecordingGroups WHERE Key=? AND Value=?", ( key, value, ) )
    if cached != None:
      o= json.loads( cached[0] )
      if o[ "latestProgramStartTime" ] == latestProgramStartTime and o[ "recordingsCount" ] == recordingsCount:
	return o[ "list" ]

    req= JSONRPC( "Control/" + uri + "/" + urllib.quote(value.encode("UTF-8")), urllib.urlencode('') )
    li= []
    for m in req:
      li.append( [ m[ "ProgramStartTime" ], m[ "RecordingId" ] ] )
      
    li= sorted(li, key=operator.itemgetter(0), reverse = True)

    o= { "latestProgramStartTime": latestProgramStartTime, "recordingsCount": recordingsCount, "list": li }
    
    cachedbc().execute("REPLACE INTO RecordingGroups VALUES( ?, ?, ? )", ( key, value, json.dumps( o ), ) )
    
    return li
    
def JSONRPC(endpoint, post):
    res= RPC( endpoint, post )
    content=  res[ "content" ]
    charset=  res[ "headers" ]['content-type'].split('charset=')[-1]    
    return json.loads( content, charset )
    
def GOOGLEIMAGERPC( tag ):
  res= JSONXRPC( "http://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=" + urllib.quote_plus( tag.encode( "UTF-8" ) ), None )
  return res[ "responseData" ][ "results" ][ 0 ][ "url" ]
    
def getCachedLatestRecordings( key, value ):
    cached= cachedbc().selectFirst("SELECT Details FROM RecordingGroups WHERE Key=? AND Value=?", ( key, value, ) )
    if cached == None: return None
    lst= json.loads( cached[0] )[ "list" ]
    return lst
    #return lst[ 0 ][ 1 ] if len( lst ) > 0 else None
    
def getLatestCachedThumbnailURL( lst, width ):
    if lst is None: return None
    for r in lst:
      path= cachePath + "%sx%d.jpg" % ( r[1], width )
  
      if os.path.exists(path) and os.path.getsize(path):
	  return path
	  
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
    
def getRecordingsGroupedByProgramTitle(programTitle,latestProgramStartTime, recordingsCount):
  return getRecordingGroup( "RecordingsForProgramTitle/Television", "ProgramTitle", programTitle, latestProgramStartTime, recordingsCount)
    
def getRecordingsGroupedByScheduleId(scheduleId,latestProgramStartTime, recordingsCount):
  return getRecordingGroup( "RecordingsForSchedule", "ScheduleId", scheduleId, latestProgramStartTime, recordingsCount)

def buildPlaybackURL(filename):
  filename= filename.replace( "\\", "/" )
  return filename_re.sub( filename_sub, filename )
  
def getThumbnailURL(id, width):
  path= cachePath + "%sx%d.jpg" % ( id, width )
  
  if not os.path.exists(path):
    tbn= RPC( "Control/RecordingThumbnail/%s/%d/0/1900-01-01" % ( id, width ), urllib.urlencode( '' ) )[ "content" ]
    f= open(path, 'wb')
    f.write(tbn)
    f.close()
    
  if os.path.getsize(path) == 0: return ''
    
  return path
  
def getThumbnailURLByTitle(title):  
  return GOOGLEIMAGERPC(title)
    
def addRecording( id, total, includeTitle ):
      d= getRecordingById( id )
      
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
	  
      tn= getThumbnailURL( d[ "RecordingId" ], 512 )

      plot= d[ "Description" ]
      tagline= date( d[ "ProgramStartTime" ] )
	  
      if d[ 'EpisodeNumberDisplay' ] != '':
	label= label + " (" + d[ 'EpisodeNumberDisplay' ] + ")"
	tagline= tagline + " - " + d[ 'EpisodeNumberDisplay' ]
      if date_label: label= label + " - " + date( d[ "ProgramStartTime" ] )
      info=  { "Plot": plot, "Tagline": tagline, "Title": subTitle }
      addDirectoryItemURL( label, "", info, tn, buildPlaybackURL( d[ "RecordingFileName" ] ), total )
      
def getGroupByFromCache( group ):
    cached= cachedbc().selectFirst("SELECT Details FROM General WHERE Key=?", ( group, ) )
    if cached != None:
      return json.loads( cached[0] )    
    return []
    
def compareGroups( g1, g2 ):
    if len( g1 ) != len( g2 ): return False
    for i in range( len( g1 ) ):
      if g1[ i ][ 1 ][ "LatestProgramStartTime" ] != g2[ i ][ 1 ][ "LatestProgramStartTime" ]: return False
      if g1[ i ][ 1 ][ "RecordingsCount" ] != g2[ i ][ 1 ][ "RecordingsCount" ]: return False
    return True
    
def loadGroupByAndRefreshThread( group ):
    req= JSONRPC( 'Control/RecordingGroups/Television/' + group, urllib.urlencode('') )
    
    li=  []
    for m in req:
      li.append( [ m[ "LatestProgramStartTime" ], m ] )

    li = sorted(li, key=operator.itemgetter(0), reverse = True)
    
    prev= getGroupByFromCache( group )
    
    if not compareGroups( li, prev ):
      notification( SListingChanged, 1000 )
      cachedbc().execute("REPLACE INTO General VALUES( ?, ? )", ( group, json.dumps( li ), ) )
      xbmc.executebuiltin("Container.Refresh()")
    
def RecordingsForScheduleId(params):
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )
    li= getRecordingsGroupedByScheduleId( params[ "ScheduleId" ], params[ "LatestProgramStartTime" ], params[ "RecordingsCount" ] )
    for l in li:
      addRecording( l[1], len(li), True )
      
def RecordingsForProgramTitle(params):
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )
    li= getRecordingsGroupedByProgramTitle( params[ "ProgramTitle" ], params[ "LatestProgramStartTime" ], params[ "RecordingsCount" ] )
    idx= 0
    for l in li:
      idx= idx + 1
      notification( SLoading % ( idx, len(li) ), 200 )
      addRecording( l[1], len(li), False )
      
def GroupBySchedule():
    start_new_thread( loadGroupByAndRefreshThread, ( "GroupBySchedule", ) )
  
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )
    li= getGroupByFromCache( "GroupBySchedule" )
    idx= 0
    for l in li:
      idx= idx + 1
      notification( SLoading % ( idx, len(li) ), 200 )
    	
      m= l[1]
      label= m[ 'ScheduleName' ] + " (" + str( m[ 'RecordingsCount' ] ) +")"
      if date_label: label= label + " - " + date( m[ "LatestProgramStartTime" ] )
      info= { "Title": m[ 'ScheduleName' ], "Tagline": date( m[ "LatestProgramStartTime" ] ) }
      params= { "ScheduleId" : m[ "ScheduleId" ], "RecordingsCount": m[ "RecordingsCount" ], "LatestProgramStartTime" : m[ "LatestProgramStartTime" ] }
      tn= getLatestCachedThumbnailURL( getCachedLatestRecordings( "ScheduleId", m[ "ScheduleId" ] ), 512 )
      tn= tn if tn else ""
      addDirectoryItem( label, "", info, tn, params, 'RecordingsForScheduleId', True, len(li) )
      
def GroupByProgramTitle():
    start_new_thread( loadGroupByAndRefreshThread, ( "GroupByProgramTitle", ) )
      
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )
    li= getGroupByFromCache( "GroupByProgramTitle" )
    idx= 0
    for l in li:
      idx= idx + 1
      notification( SLoading % ( idx, len(li) ), 200 )

      m= l[1]
      label= m[ 'ProgramTitle' ] + " (" + str( m[ 'RecordingsCount' ] ) +")"
      if date_label: label= label + " - " + date( m[ "LatestProgramStartTime" ] )
      info= { "Title": m[ 'ProgramTitle' ], "Tagline": date( m[ "LatestProgramStartTime" ] ) }
      params= { "ProgramTitle" : m[ "ProgramTitle" ], "RecordingsCount": m[ "RecordingsCount" ], "LatestProgramStartTime" : m[ "LatestProgramStartTime" ] }
      tn= getLatestCachedThumbnailURL( getCachedLatestRecordings( "ProgramTitle", m[ "ProgramTitle" ] ), 512 )
      tn= tn if tn else ""
      addDirectoryItem( label, "", info, tn, params, 'RecordingsForProgramTitle', True, len(li) )   
      
def ListProgramTitleLatest():
    start_new_thread( loadGroupByAndRefreshThread, ( "GroupByProgramTitle", ) )
  
    xbmcplugin.setContent( int(sys.argv[1]), "episodes" )  

    li= getGroupByFromCache( "GroupByProgramTitle" )
    idx= 0
    for l in li:
      idx= idx + 1
      notification( SLoading % ( idx, len(li) ), 200 )
    
      m= l[1]
      lis= getRecordingsGroupedByProgramTitle( m[ "ProgramTitle" ], m[ "LatestProgramStartTime" ], m[ "RecordingsCount" ] )
      if len( lis ) > 0:
	addRecording( lis[0][ 1 ], len(li), True )
	
# call main!
main()
