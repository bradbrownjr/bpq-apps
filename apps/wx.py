#!/usr/bin/python3
# This script requires w3m which may not be installed by default on your OS
# sudo apt-get install w3m

import os
menu = """
Weather Services
------------------------------------------
1) Maine/New Hampshire Weather Summary
2) Maine/New Hampshire Weather Roundup
3) Western Maine/New Hampshire Forecast
4) Northern and Eastern Maine Forecast
5) Maine/New Hampshire Max/Min Temperature 
   and Precipitation Table
------------------------------------------
6) About this application
0) Return to node

Information is retrieved from 
https://www.maine.gov/mema/weather/general-information
"""

about = """
This is a Python3 script which pulls data from weather.gov
reports and displays them on the screen using the w3m -dump
utility.

Enter the number of the report to retrieve it. If the report
is blank or cuts off too early, you may have encountered the
BBS node's app timeout. Try again if nothing was retrieved.
"""

print (menu)
while True:
	selected = int(input ("Select an application: "))

	if selected == 1:
        	os.system("/usr/bin/w3m https://w1.weather.gov/data/GYX/RWSGYX -dump")
	elif selected == 2:
        	os.system("/usr/bin/w3m http://www.weather.gov/data/GYX/RWRGYX -dump")
	elif selected == 3:
        	os.system("/usr/bin/w3m http://www.weather.gov/data/GYX/SFTGYX -dump")
	elif selected == 4:
        	os.system("/usr/bin/w3m http://www.weather.gov/data/CAR/SFTCAR -dump")
	elif selected == 5:
        	os.system("/usr/bin/w3m http://www.weather.gov/data/GYX/RTPGYX -dump")
	elif selected == 6:
		print (about)
	elif selected == 0:
		print ("\nExiting...\n")
		exit()
