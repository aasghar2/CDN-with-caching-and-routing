#!/usr/bin/python3

#importing modules
from http.server import BaseHTTPRequestHandler,HTTPServer
import time
import sys
import os
import json
import requests
import threading
from threading import Thread
import socket
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
import datetime


#get data from json file
with open(sys.argv[1]) as json_data_file:
	data = json.load(json_data_file)

#caching scheme
CACHING_SCHEME = int(sys.argv[2])

#setting max. link-delay constant
MAX_LINK_DELAY = 10

#assign values
NODE_NAME = data['node_name']
NODE_IP = data['node_ip']
NODE_PORT = data['node_port']
NODE_GEO_TAG = data['geo_tag']
NODE_LOG_FILE = data['log_file']
NODE_LINKS = data['links']
CONTENT_IP = data['content_ip']
CONTENT_PORT = data['content_port']

#local node address
localnodename = NODE_IP+':'+NODE_PORT

#neighbor table for directly connected nodes
NEIGHBOR_TABLE = {}

#creating table for neighboring nodes
for i in NODE_LINKS:

	#storing node address as tuple of (ip_address,port)
	node = (i['node_ip'],i['node_port'])

        #values will be added later for each directly connected node
	NEIGHBOR_TABLE.update({node:{}})


#create log file
open(NODE_LOG_FILE, "w+").write("Logging starts...\n")

#routing table for all nodes in topology
ROUTE_TABLE = {}

#image file extension list
image_ext = ['.jpg', '.png', '.gif', '.jpeg']

#function for logging events
def logging(eventtime,node_message):
	print("[%s] - %s - - %s\n" %(eventtime,localnodename,node_message))
	open(NODE_LOG_FILE, "a").write("[%s] - %s - - %s\n" %(eventtime,localnodename,node_message))

#ping pong and delay count function
def pingpong():
	
	#infinitely run this function
	while True:
		
		#ping directly connected nodes
		for i in NODE_LINKS:

			#requesting device address
			nodename = i['node_ip']+':'+i['node_port']

			#requesting URL
			ping_url = 'http://'+nodename+'/ping'
			
			#link delay identified in conf file
			delay = i['link_delay']
			
			#adding header field with local node address
			headers = {'client-address': localnodename}

			#get current time for delay count
			start_time = time.time()
			
			#put delay before sending request
			time.sleep(float(delay))

			#stop program from being stopped due to error in request
			try:
				req = requests.get(ping_url,headers=headers)
			
			#when request is not successful
			except:
				logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'GET '+ping_url+' '+'Error in Connection')
							
				#updating link-delay, check if previously live node is down
				if 'link_delay' in NEIGHBOR_TABLE[(i['node_ip'],i['node_port'])]:
					
					#setting link-delay to max. constant value
					NEIGHBOR_TABLE[(i['node_ip'],i['node_port'])]['link_delay'] = MAX_LINK_DELAY

				#ignore this node if request not successful
				continue
			
			#proceeds below if response is received
			logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'GET '+ping_url+' '+str(req.status_code))
			
			#if response is OK
			if req.status_code == 200:

				#get geo-tag from received ping response
				node_geo_tag = req.headers['geo-tag']

				#total time taken for this request
				link_delay = time.time() - start_time
				
				#getting one direction delay
				cost = float(link_delay/2)

				#add geo-tag & CALCULATED delay values in neighbor_table
				NEIGHBOR_TABLE[(i['node_ip'],i['node_port'])].update({'geo_tag':node_geo_tag,'link_delay':cost})

		#run this function again after 30 sec 
		sleeptime = 30

		#if any of the mentioned neighbors not discovered yet, then run the function quickly (5sec)
		for link in NEIGHBOR_TABLE:

			#if node is discovered then there must be CALCULATED link-delay information
			if 'link_delay' not in NEIGHBOR_TABLE[link]:
				sleeptime = 5

			#if node got down, reduce sleep time to update link ASAP
			elif NEIGHBOR_TABLE[link]['link_delay'] >= MAX_LINK_DELAY:
				sleeptime = 5

		#sleep before starting again
		time.sleep(sleeptime)

#function for distance vector routing algorithm
def dvr():

	#run infinitely
	while True:
		
		#initialize the advertising routing table as payload
		payload = {'dvr':[]}

		#update entries in routing table
		for node in NEIGHBOR_TABLE:

			#neglect neighbor that has not responded
			if 'link_delay' not in NEIGHBOR_TABLE[node]:
				continue

			#add the live neighbor recent values in routing table
			ROUTE_TABLE.update({(node[0], node[1]):{'geo_tag':NEIGHBOR_TABLE[node]['geo_tag'], 'link_delay':NEIGHBOR_TABLE[node]['link_delay'], 'next_hop':localnodename}})
		
		#creating dvr payload from routing table
		for node in ROUTE_TABLE:

			#adding values in class format
			payload['dvr'].append({'destination_ip':node[0],'destination_port':node[1],'geo_tag':ROUTE_TABLE[node]['geo_tag'], 'link_delay':ROUTE_TABLE[node]['link_delay']})			

		#sending payload to neighbors
		for node in NEIGHBOR_TABLE:

			#neglecting neighbor that has not responded
			if 'link_delay' not in NEIGHBOR_TABLE[node]:
				continue

			#requesting node address = ipaddress + port
			hostname = node[0]+':'+node[1]

			#requesting URL for DVR
			dvr_url = 'http://'+hostname+'/dvr'

			#adding sending node geo-tag & address with other headers 
			headers = {'geo-tag': NODE_GEO_TAG, 'client-address': localnodename, 'Content-Type': 'Application/json', 'Content-length': str(len(json.dumps(payload)))}

			#adding CALCULATED delay before sending request
			time.sleep(float(NEIGHBOR_TABLE[node]['link_delay']))

			#stop program from being stopped due to error in request
			try:
				dvr_req = requests.post(url=dvr_url, headers=headers, data=json.dumps(payload))
				logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'POST '+dvr_url+' '+str(dvr_req.status_code))
			except:
				logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'POST '+dvr_url+' '+'Error in Connection')
				
				#ignore this node if request not successful
				continue

		#run this function after every 30sec			
		time.sleep(30)

# This class handles any incoming request from the browser
class HTTPServerRequestHandler(BaseHTTPRequestHandler):

    # Handler for the GET requests
	def do_GET(self):

		#get URL from request line
		req = self.requestline.split(' ')
		url = urlparse(req[1])
		
		#check cache first
		if os.path.isfile('./' + NODE_GEO_TAG + url.path):

			# Send response code and headers
			self.send_response(200)

			#finding file extension
			file_ext = os.path.splitext('/' + NODE_GEO_TAG + url.path)

			#set content-type header field to image if file is image
			if file_ext[1] in image_ext:
				self.send_header('Content-type', 'image')
			
			#set content-type header field to text/html for all other type files
			else:
				self.send_header('Content-type', 'text/html')

			#set content-length header field by finding size of file
			self.send_header('Content-length', str(os.stat('./' + NODE_GEO_TAG + url.path).st_size))
			
			self.end_headers()

			# Send the file in binary format
			with open('./' + NODE_GEO_TAG + url.path, 'rb') as f:
				self.wfile.write(f.read())
		
		
		#if request is for this region (geo-tag)
		elif url.netloc == NODE_GEO_TAG:

			#stop program from being stopped due to error in request
			try:
				
				#sending request to content server with requested URL path
				content = requests.get('http://'+CONTENT_IP+':'+CONTENT_PORT+url.path)

				#flag for connection refused by remote host
				ConnectionRefused = False
				logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'GET '+'http://'+CONTENT_IP+':'+CONTENT_PORT+url.path+' '+str(content.status_code))
			
			except:
				
				#set flag if connection refused by remote host
				ConnectionRefused = True
				logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'GET '+'http://'+CONTENT_IP+':'+CONTENT_PORT+url.path+' ConnectionRefuse')
			
			#if connection accepted then proceed
			if ConnectionRefused == False:

				#send the same reponse code as received	
				self.send_response(content.status_code)

				#if response is OK
				if content.status_code == 200:

					#get actual content from response
					data = content.content

					#storing content in cache
					#make the file in directory
					os.makedirs(os.path.dirname(NODE_GEO_TAG + url.path), exist_ok=True)

					#write content to file in binary
					open(NODE_GEO_TAG + url.path, "wb").write(data)

					#send header based on cache scheme
					if CACHING_SCHEME == 2:
						
						#send flag for content being cached for cache scheme 2
						self.send_header('Cached','True')

					#send other header fields and data
					self.send_header('Content-type',content.headers['content-type'])
					self.send_header('Content-length',content.headers['content-length'])
					self.end_headers()
					self.wfile.write(data)

				#send invalid response code if correct response not received
				else:
					self.send_response(404)
		
		#if request is for other hostname
		elif url.netloc not in NODE_GEO_TAG:

			#flag if route found or not
			NEXT_HOP_FOUND = False

			#finding the route to requested geo_tag
			for node in ROUTE_TABLE:

				#matching the destination node geo_tag with url hostname
				if url.netloc == ROUTE_TABLE[node]['geo_tag']:

					#setting flag true since route is found
					NEXT_HOP_FOUND = True

					#get the next hop for the destination node in routing table
					next_hop = ROUTE_TABLE[node]['next_hop']

					#splitting the next_hop for finding delay
					next_hop_split = next_hop.split(':')

					#check if next_hop is the local node
					if next_hop == localnodename:

						#get the link delay and set proxy to destination node
						link_delay = ROUTE_TABLE[node]['link_delay']
						http_proxy = node[0]+':'+node[1]

					#set the link delay and proxy from routing table if next_hop not local node
					else:
						#splitting the next_hop for finding delay
						next_hop_split = next_hop.split(':')
						
						#get link_delay from route table and set proxy to next_hop in route table
						link_delay = ROUTE_TABLE[(next_hop_split[0],next_hop_split[1])]['link_delay']
						http_proxy = next_hop

					#setting up proxy
					proxyDict = { "http":http_proxy,"https":""}

					#check if next-hop reachable (link-delay must be less than MAX_LINK_DELAY)
					if link_delay < MAX_LINK_DELAY:
					
						#Put CALCULATED delay before sending request to destination node
						time.sleep(float(link_delay))

						#stop program from being stopped due to error in request
						try:

							#set http request with proxy
							content = requests.get(req[1],proxies=proxyDict,headers=self.headers)
							ConnectionRefused = False
							logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'GET '+req[1]+' '+str(content.status_code))
						except:
							ConnectionRefused = True
							logging(datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S"),'GET '+req[1]+' Connection Refused')
							self.send_response(404)

						#if connection is successful
						if ConnectionRefused == False:

							#send the received response code
							self.send_response(content.status_code)
		
							#proceed if status code is OK
							if content.status_code == 200:

								#get content from response received
								data = content.content

								#check caching scheme
								if CACHING_SCHEME == 2:

									#if data not cached already
									if 'Cached' not in content.headers:

										#cache the content when there is no flag of cached
										#make the file in directory
										os.makedirs(os.path.dirname(NODE_GEO_TAG + url.path), exist_ok=True)

										#write data to file
										open(NODE_GEO_TAG + url.path, "wb").write(data)

										#add header of data is Cached
										self.send_header('Cached','True')

									#if data cached already
									else:

										#send cached header field
										self.send_header('Cached',content.headers['Cached'])	

								#for caching scheme 1
								else:

									#make the file in directory
									os.makedirs(os.path.dirname(NODE_GEO_TAG + url.path), exist_ok=True)

									#write data to file
									open(NODE_GEO_TAG + url.path, "wb").write(data)

								#check for other imp headers and send their values and data
								if 'content-type' in content.headers:
									self.send_header('Content-type',content.headers['content-type'])
								if 'content-length' in content.headers:
									self.send_header('Content-length',content.headers['content-length'])
								self.end_headers()
								self.wfile.write(data)

					#if link_delay > MAX_LINK_DELAY then send next-hop unreachable message
					else:
						self.send_response(0)
					
					#break loop since route found
					break

			#if route not found				
			if NEXT_HOP_FOUND == False:

				#send response of unreachable address
				self.send_response(0)

		#TESTING response		
		elif self.path == "/":

			# Send response with headers and html message
			self.send_response(200)
			self.send_header('Content-type','text/html')
			message = "<html><body>It Works</body></html>"
			self.send_header('Content-length', len(message))
			self.end_headers()
			self.wfile.write(message.encode())
		
		#PING response
		elif self.path == "/ping":

			#finding the requesting node in directly connected nodes list
			for i in NODE_LINKS:

				node_address = i['node_ip']+':'+i['node_port']

				#match the incoming message address with node_address in connected nodes list
				if self.headers['client-address'] == node_address:

					#put delay before sending response
					time.sleep(float(i['link_delay']))

			#send required headers and message
			self.send_response(200)
			self.send_header('Content-type','text/html')
			message = 'pong'
			self.send_header('Content-length', len(message))
			self.send_header('geo-tag',NODE_GEO_TAG)
			self.end_headers()

			#convert message to binary before sending
			self.wfile.write(message.encode())
		
		#for all other scenarios
		else:

			# Send 404 (Not Found) status code for any other requests
			self.send_response(404)


		return

	#Handler for the POST requests
	def do_POST(self):
		 
		#dvr response
		if self.path == "/dvr":
			#ref: https://stackoverflow.com/questions/5975952/how-to-extract-http-message-body-in-basehttprequesthandler-do-post
			#get the payload length of response
			content_len = int(self.headers['Content-length'])

			#get requesting node geo_tag and address from headers
			other_geo_tag = self.headers['geo-tag']
			other_address = self.headers['client-address']

			#split requesting node address to find it in route table
			other_address_split = other_address.split(':')

			#get dvr payload and convert it to python dictionary using json
			post_body = json.loads(self.rfile.read(content_len).decode())

			#check if dvr message received from known destination
			if (other_address_split[0],other_address_split[1]) in NEIGHBOR_TABLE:

				#updating routing table based on incoming DVR message
				for link in post_body['dvr']:

					#add the next_hop link_delay to link_delay in received routing advertisement
					link_delay = ROUTE_TABLE[(other_address_split[0],other_address_split[1])]['link_delay']+float(link['link_delay'])
				
					#neglect route for local node
					if link['destination_ip']+':'+link['destination_port'] == localnodename:
						continue
				
					#if unknown destination node
					elif (link['destination_ip'], link['destination_port']) not in ROUTE_TABLE:

						#add it to routing table
						ROUTE_TABLE.update({(link['destination_ip'], link['destination_port']):{'link_delay':link_delay, 'geo_tag':link['geo_tag'], 'next_hop':other_address}})
				
					#if known destination route with lesser delay
					elif link_delay < ROUTE_TABLE[(link['destination_ip'], link['destination_port'])]['link_delay']:

						#change the route delay and next_hop
						ROUTE_TABLE[(link['destination_ip'], link['destination_port'])]['link_delay'] = link_delay #updating entry
						ROUTE_TABLE[(link['destination_ip'], link['destination_port'])]['next_hop'] = other_address #updating next_hop
				

			#send response with OK
			self.send_response(200)
			self.end_headers()

		#for all other POST requests
		else:
			# Send 404 (Not Found) status code
			self.send_response(404)
		return

	#function for log messages in HTTPRequestHandler
	def log_message(self, format, *args):
		print("[%s] - %s - - %s\n" %(self.log_date_time_string(),self.address_string(),format%args))
		open(NODE_LOG_FILE, "a").write("[%s] - %s - - %s\n" %(self.log_date_time_string(),self.address_string(),format%args))

#threading HTTP Request server
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

#function to intialize threading HTTP server
def runHTTPServer():

	#start threaded http server on local node address
	server = ThreadedHTTPServer((NODE_IP, int(NODE_PORT)), HTTPServerRequestHandler)
	print('Starting CDN server at port '+NODE_PORT+', use <Ctrl-C> to stop')
	server.serve_forever()


#main function of the setup
if __name__ == '__main__':

	#Multiprocess threading ref: https://stackoverflow.com/questions/2957116/make-2-functions-run-at-the-same-time

	#start multiple continous running functions simltaneously
	Thread(target = pingpong).start()
	Thread(target = runHTTPServer).start()
	
	#little delay before starting dvr
	time.sleep(5)

	#start dvr process
	Thread(target = dvr).start()
