import string,cgi,time
from os import curdir, sep

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
 
import os, shutil
 
path= os.path.abspath('./cache')
 
# -----------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
    fn= path + self.path
    if not os.path.exists( fn ):
      self.send_response(404)
      self.end_headers()
      return
    f= open( fn, "rb" )
    self.send_response(200)
    self.send_header('Content-type','image/jpeg')
    self.send_header('Content-length',os.path.getsize(fn))
    self.end_headers()
    self.wfile.write(f.read())
    f.close()
  def do_HEAD(self):
    fn= path + self.path
    if not os.path.exists( fn ):
      self.send_response(404)
      self.end_headers()
      return
    self.send_response(200)
    self.send_header('Content-type','image/jpeg')
    self.send_header('Content-length',os.path.getsize(fn))
    self.end_headers()
  def do_PUT(self):
    fn= path + self.path
    d= os.path.dirname( fn )
    if not os.path.exists( d ): os.makedirs(d)    
    f= open( fn + ".temp", "wb" )
    length = int(self.headers['Content-Length'])
    f.write(self.rfile.read(length))
    f.close()
    os.rename( fn + ".temp", fn )
    self.send_response(200)
    self.end_headers()
  def do_DELETE(self):
    f= path + self.path
    if os.path.exists(f):
      if os.path.isfile(f): os.remove(f)
      else: shutil.rmtree( f )
    self.send_response(200)
    self.end_headers()
 
server= HTTPServer(('', 8080), Handler)
server.serve_forever()
