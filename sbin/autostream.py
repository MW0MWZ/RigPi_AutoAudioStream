#!/usr/bin/python

#   Copyright (C) 2020 by Andrew Taylor (MW0MWZ)
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

###############################################################################
#                                                                             #
#                        RigPi Auto Streaming Control                         #
#                                                                             #
#    Version 1.0, Code, Design and Development by Andy Taylor (MW0MWZ).       #
#                                                                             #
###############################################################################

import subprocess
import time
import os
import linecache
import datetime
import commands
import requests
import mysql.connector
import logging

# Debugging
debug = 0

# HRDLog.net Static Information
callsign = "M1ABC"
code = "fffffffffff"

# Streaming Destination
streamDest = "http://1.1.1.1/stream.ffm"

# Log file
outputLog = "/var/log/autostream.log"

###############################################################################
#                                                                             #
#                             Do not edit below                               #
#                                                                             #
###############################################################################

# Setup Logging
logging.basicConfig(
	filename=outputLog,level=logging.DEBUG,
	format='%(asctime)s %(levelname)-8s %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S')

logging.getLogger('requests').setLevel(logging.WARNING)
logging.info('StartUp - Auto Audio Stream by Andy Taylor (MW0MWZ)')

# SQL Database Info
sqlUsername = subprocess.check_output("grep \"sql_radio_username\" /var/www/html/programs/sqldata.php | awk -F '\"' '{print $2}'", shell=True).rstrip()
sqlPassword = subprocess.check_output("grep \"sql_radio_password\" /var/www/html/programs/sqldata.php | awk -F '\"' '{print $2}'", shell=True).rstrip()

mydb = mysql.connector.connect(
	host="localhost",
	user=sqlUsername,
	passwd=sqlPassword,
	database="station"
)

# Get the active radio from the database
mycursor = mydb.cursor()
mycursor.execute("SELECT Manufacturer,Model from MySettings where Selected = '1'")
myresult = mycursor.fetchall()
for data in myresult:
        radioMake = data[0]
        radioModel = data[1]
radio = radioMake + ' ' + radioModel

while True: #Main loop
	# Check and see if rigctld is running or not
	checkprocrigctld = subprocess.Popen('/usr/bin/pgrep rigctld', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	if not checkprocrigctld.stdout.readlines():
		# rigctld is not running kill the stream and wait 60 secs
		checkstreamStatus = subprocess.Popen('/usr/bin/pgrep arecord', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		if not checkstreamStatus.stdout.readlines():
			# Already not running
			time.sleep(0)
		else:
			# Kill the active Stream
			os.system('/usr/bin/killall arecord 2> /dev/null')
			os.system('/usr/bin/killall ffmpeg 2> /dev/null')
			if int(debug) == 1:
				logging.debug('Stopping active stream')
		checkstreamStatus.wait()
		if int(debug) == 1:
			logging.debug('Radio CAT Dissabled')
		time.sleep(60)
	else:
		# rigctld is running
		powerstatus = commands.getstatusoutput('/usr/local/bin/rigctl -m 2 \get_powerstat')
		if not "error" in powerstatus[1]:
			# Rig Communication is OK, Get the Frequency
			freq = commands.getstatusoutput('/usr/local/bin/rigctl -m 2 \get_freq')
			freqNum = int((freq[1].splitlines( ))[0])
			freqOut = "{:,}".format(freqNum).replace(",", ".")
			if freqNum >= 1000000:
				suffix = " MHz"
			elif freqNum >= 1000:
				suffix = " KHz"
			else:
				suffix = " Hz"

			# Get the Mode
			mode = commands.getstatusoutput('/usr/local/bin/rigctl -m 2 \get_mode')
			mode = (mode[1].splitlines( ))[0]

			# Output
			output = "OnAir: " + freqOut + suffix + ' ' + mode
			if not "error" in output:
				# Post Radio Data to HRDLog.net
				timeStamp = time.time()
				url = 'http://robot.hrdlog.net/OnAir.aspx'
				myobj = {'Frequency': freqNum, 'Mode': mode, 'Radio': radio, 'Callsign': callsign, 'Code': code}
				postOut = requests.post(url, data = myobj)

				if int(debug) == 1:
					logging.debug(output)
					logging.debug(postOut.text)

			else:
				del output

			# Check the stream, it should be running, clean up and start it.
			checkstreamStatus = subprocess.Popen('/usr/bin/pgrep arecord', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			if not checkstreamStatus.stdout.readlines():
				# ffmpeg is not running
				os.system('/usr/bin/killall arecord 2> /dev/null')
				os.system('/usr/bin/killall ffmpeg 2> /dev/null')
				logging.info('Staring Stream')
				os.system('/usr/bin/arecord -f dat -D dsnoop:0,0 2> /dev/null | /usr/bin/ffmpeg -thread_queue_size 128 -i - -af "highpass=f=300, lowpass=f=2800" -acodec libmp3lame -ab 32k -ac 1 -ar 11025 ' + streamDest + ' > /dev/null 2>&1 &')
				time.sleep(3)
			checkstreamStatus.wait()

		else:
			# Rig Communication is NOT OK, Dump the stream.
			checkstreamStatus = subprocess.Popen('/usr/bin/pgrep arecord', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			if not checkstreamStatus.stdout.readlines():
				# Already not running
				time.sleep(0)
			else:
				# Kill the active Stream
				os.system('/usr/bin/killall arecord 2> /dev/null')
				os.system('/usr/bin/killall ffmpeg 2> /dev/null')
				logging.info('Stopping active stream')
			checkstreamStatus.wait()
			logging.info('Radio CAT Error')
			time.sleep(60)

		# OK We're done.
	checkprocrigctld.wait()

	# This is the 15 second sleep before the next pass.
	time.sleep(15)
