#!/usr/bin/python3

#importing modules
from http.server import BaseHTTPRequestHandler,HTTPServer
import time
import sys
import os
import json
import requests
import threading
import socket
from socketserver import ThreadingMixIn

#assign values
SERVER_IP = sys.argv[1]
SERVER_PORT = sys.argv[2]

#list to check image extensions
image_ext = ['.jpg', '.png', '.gif', '.jpeg']

#start logging
open('CONTENT-SERVER_LOG.log', "w+").write('Logging started...')

# This class handles any incoming request from the browser
class HTTPServerRequestHandler(BaseHTTPRequestHandler):

        # Handler for the GET requests
	def do_GET(self):

		#testing page
		if self.path == "/":

        	# Send response code and headers
			self.send_response(200)

			#testing message
			message = '<html><body>Welcome to Home Page</body></html>'
			self.send_header('Content-type','text/html')
			self.send_header('Content-length', len(message))
			self.end_headers()
			
			#send home page content
			self.wfile.write(message.encode())

		#if requested path exist in content-server
		elif os.path.isfile('.' + self.path):

                        # Send response code and headers
			self.send_response(200)

			#get file extension
			file_ext = os.path.splitext(self.path)

			#check if its image
			if file_ext[1] in image_ext:

				#set content-type to image
				self.send_header('Content-type', 'image')

			#for other types
			else:

				#set content-type to text/html
				self.send_header('Content-type', 'text/html')

			#get file size and send it in header field
			self.send_header('Content-length', str(os.stat('.' + self.path).st_size))
			
			#ending headers portion
			self.end_headers()
			
                        # Send the content in binary format
			with open('./' + self.path, 'rb') as f:
				self.wfile.write(f.read())

		#for all other types of request
		else:
                        # Send 404 (Not Found) status code
			self.send_response(404)
		
		return

	#log message function
	def log_message(self, format, *args):
		print("[%s] - %s - - %s\n" %(self.log_date_time_string(),self.address_string(),format%args))
		open('CONTENT-SERVER_LOG.log', "a").write("[%s] - %s - - %s\n" %(self.log_date_time_string(),self.address_string(),format%args))

#from https://stackoverflow.com/questions/14088294/multithreaded-web-server-in-python
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


#main function
if __name__ == '__main__':

	#start threaded http server
	server = ThreadedHTTPServer((SERVER_IP, int(SERVER_PORT)), HTTPServerRequestHandler)
	print('Starting Proxy server at port '+SERVER_PORT+', use <Ctrl-C> to stop')
	server.serve_forever()

