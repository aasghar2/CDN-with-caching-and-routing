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
from urllib.parse import urlparse
import datetime

#assign values
PROXY_IP = sys.argv[1]
PROXY_PORT = sys.argv[2]
CDN_IP = sys.argv[3]
CDN_PORT = sys.argv[4]

#create logging file
open('PROXY_LOG.log', "w+").write("Logging Starts...")

#storing local node address in variable
localnodename = PROXY_IP+':'+PROXY_PORT

#function for logging events
def logging(eventtime,node_message):
	print("[%s] - %s - - %s\n" %(eventtime,localnodename,node_message))
	open('PROXY_LOG.log', "a").write("[%s] - %s - - %s\n" %(eventtime,localnodename,node_message))


# This class handles any incoming request from the browser
class HTTPServerRequestHandler(BaseHTTPRequestHandler):


        # Handler for the GET requests
	def do_GET(self):

		#get url from request line
		req = self.requestline.split(' ')
		url = req[1]

		#parse url
		urlinfo = urlparse(url)

		#setting given CDN server as proxy
		http_proxy  = CDN_IP+":"+CDN_PORT

		#creating proxy dictionary, required by request method
		proxyDict = { "http":http_proxy,"https":""}

		#stop program from being stopped due to request errors
		try:
			content = requests.get(url, proxies=proxyDict)
			logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'GET '+url+' '+str(content.status_code))
			
			#flag for connection status
			connectionFailed = False
			
		except:

			#connection not successful, set flag
			connectionFailed = True
			logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'GET '+url+' Connection Refused')
        	
		#check connection flag
		if connectionFailed == False:

			#if response status OK then proceed
			if content.status_code == 200:

					#send response headers
					self.send_response(content.status_code)
					self.send_header('Content-type',content.headers['content-type'])
					self.send_header('Content-length',content.headers['content-length'])
					self.end_headers()

					#send content recieved
					data = content.content
					self.wfile.write(data)

			#for all other responses
			else:
                        	# Send 404 (Not Found) status code
				self.send_response(404)
		return

	#logging function
	def log_message(self, format, *args):
		print("[%s] - %s - - %s\n" %(self.log_date_time_string(),self.address_string(),format%args))
		open('PROXY_LOG.log', "a").write("[%s] - %s - - %s\n" %(self.log_date_time_string(),self.address_string(),format%args))

#from https://stackoverflow.com/questions/14088294/multithreaded-web-server-in-python
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

#main function
if __name__ == '__main__':

	#start threaded http server
	server = ThreadedHTTPServer((PROXY_IP, int(PROXY_PORT)), HTTPServerRequestHandler)
	print('Starting Proxy server at port '+PROXY_PORT+', use <Ctrl-C> to stop')
	server.serve_forever()

