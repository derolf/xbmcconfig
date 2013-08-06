# (C) dero, based on jhh's initial XBMC-4tr "simple" client

import os
import json, urllib2
from settings import *

def EXISTS( *args ):
    path= cachePath
    for key in args:
      path= path + "/" + str(key)
      
    try: s= urllib2.urlopen(path)
    except urllib2.HTTPError, e:
      if e.code == 404: return False
      raise e
    return True
  
def URL( *args ):
    path= cachePath
    for key in args:
      path= path + "/" + str(key)
    return path

def XGET( *args ):
    path= cachePath
    for key in args:
      path= path + "/" + str(key)
      
    try: s= urllib2.urlopen(path)
    except urllib2.HTTPError, e:
      if e.code == 404: return None
      raise e
    v= s.read()
    s.close()
    return v
  
def XPUT( *args ):
  path= cachePath
  args= list(args)
  value= args.pop()
  
  for key in args:
    path= path + "/" + str(key)
    
  opener = urllib2.build_opener(urllib2.HTTPHandler)
  
  if value is not None:
    request = urllib2.Request(path, data=value)
    request.get_method = lambda: 'PUT'
  else:
    request = urllib2.Request(path)
    request.get_method = lambda: 'DELETE'
  opener.open(request).close()
  
def GET( *args ):
  v= XGET( *args )
  return json.loads( v ) if v is not None else None
  
def PUT( *args ):
  path= cachePath
  args= list(args)
  v= args.pop()
  v= json.dumps( v ) if v is not None else None
  args.append( v )
  XPUT( *args )

# check/recreate cache schema
def checkSchema():
  try: v= GET( "General", "Version" )
  except: v= None
  if v == None or int(v) < 4:
    print "Schema changed, dropping cache...\n"
    PUT( None )
    PUT( "General", "Version", 4 );
    
