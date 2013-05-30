# (C) dero, based on jhh's initial XBMC-4tr "simple" client

import os
import json, shutil
from settings import *

def GET( *args ):
  path= cachePath
  for key in args:
    path= path + "/" + str(key)
  
  try: f= open(path + ".json", 'rb')
  except: return None
  v= json.load( f )
  f.close()
  return v

def PUT( *args ):
  path= cachePath
  args= list(args)
  value= args.pop()
  
  for key in args:
    try: os.mkdir( path )
    except: pass
    path= path + "/" + str(key)
    
  f= open(path + ".json", 'w')
  json.dump( value, f )
  f.close()

# check/recreate cache schema
def checkSchema():
  v= GET( "General", "Version" )
  if v == None or int(v) < 4:
    print "Schema changed, dropping cache...\n"
    shutil.rmtree( cachePath )
    os.mkdir( cachePath )
    os.mkdir( cachePath + "/thumbs" )
    PUT( "General", "Version", 4 );
    
