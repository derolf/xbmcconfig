# (C) dero, based on jhh's initial XBMC-4tr "simple" client

import urllib, urllib2, os
import json, threading, shutil, operator
from threading import Thread, Lock
from shared import *

# globals
ip_addr= 	"htpc"
ip_port= 	"49943"
webaddress= 	"http://" + ip_addr + ":" + ip_port

    
# call 4TR    
def RPC(endpoint, post):
    url=      webaddress + '/ForTheRecord/' + endpoint
    print "Calling FTR: " + url
    WebSock=  urllib2.urlopen(url, post)
    content=  WebSock.read()
    headers=  WebSock.headers
    WebSock.close()
    return { "content": content, "headers" : headers }
    
def JSONRPC(endpoint, post):
    res= RPC( endpoint, post )
    content=  res[ "content" ]
    charset=  res[ "headers" ]['content-type'].split('charset=')[-1]    
    return json.loads( content, charset )
  
def dictFromList( li, key ):
    res = {}
    for m in li:
      res[ m[key] ]= m
    return res
  
def threadFine( func ):
  def wrap(*args):
    func( *args )
    threading.currentThread().fine= True      
  return wrap
  
def updateThumbnail(id, width):
  path= "%sx%d.jpg" % ( id, width )
  if not EXISTS( "Thumbs", path ):
    tbn= RPC( "Control/RecordingThumbnail/%s/%d/0/1900-01-01" % ( id, width ), urllib.urlencode( '' ) )[ "content" ]
    XPUT( "Thumbs", path, tbn )
    
def updateGroup( groups, group, groupid, uri ):
    recs= GET( "Group", groups, groupid )
    if recs is None: recs= {}
      
    recslock= Lock()
    threads= []
    
    req= JSONRPC( "Control/" + uri + "/" + urllib.quote(group.encode("UTF-8")), urllib.urlencode('') )
    for m in req:
      id= m[ "RecordingId" ]
      if id in recs: continue
      
      updateThumbnail( id, 512 )
      recs[ id ]= JSONRPC( 'Control/RecordingById/' + id, urllib.urlencode('') )
      
    PUT( "Group", groups, groupid, recs )
    
def updateGroups( groups, groupkey, uri ):
    cached= GET( "Group", groups, "_" )
    if cached is None: cached= {}
    
    ID= 0
    for items in cached.values():
      if items[ "ID" ] > ID: ID= items[ "ID" ]

    threads= []
    
    req= JSONRPC( 'Control/RecordingGroups/Television/' + groups, urllib.urlencode('') )
    for m in req:
      group= m[ groupkey ]
      if group in cached:
	cm= cached[ group ]
	if cm["LatestProgramStartTime"] == m["LatestProgramStartTime"] and cm["RecordingsCount"] == m["RecordingsCount"]: continue
	m[ "ID" ]= cm[ "ID" ]
      else:
        ID= ID + 1
	m[ "ID" ]= ID
	
      cached[ group ]= m
      
      t= Thread( target=threadFine(updateGroup), args=( groups, group, m[ "ID" ], uri ) )
      t.start()
      threads.append( t  )
      
    for t in threads:
      t.join()
      t.fine
      
    for cm in cached.values():      
      li= GET( "Group", groups, cm[ "ID" ] ).values()
      li= sorted(li, key=operator.itemgetter("ProgramStartTime"), reverse = True)      
      cm["Latest"]= li[0] if len(li)>0 else None
      
    PUT( "Group", groups, "_", cached )
    

try: os.mkdir( cachePath )
except: pass
     
checkSchema()
updateGroups("GroupBySchedule","ScheduleId", "RecordingsForSchedule")
updateGroups("GroupByProgramTitle","ProgramTitle", "RecordingsForProgramTitle/Television")
