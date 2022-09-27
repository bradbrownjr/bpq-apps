#!/usr/bin/python3
import os
menu = """
Space Weather Reports
------------------------------------------
1) Forecast Discussion
2) 3-Day Forecast
3) 3-Day Geomagnetic Forecast
4) 3-day Space Weather Predictions
5) Advisory Outlook
6) Weekly Highlights and Forecasts
7) Geophysical Alert Message
------------------------------------------
9) About this application
0) Return to node

Information is retrieved from https://www.swpc.noaa.gov/
"""

about = """
This is a Python3 script which pulls data from
https://services.swpc.noaa.gov/text/ and displays
them on the screen using the w3m utility.

Enter the number of the report to retrieve it. If the report
is blank or cuts off too early, you may have encountered the
BBS node's app timeout. Try again if nothing was retrieved.
"""

print (menu)
while True:
        selected = int(input ("Select an application: "))

        if selected == 1:
                os.system("/usr/bin/w3m https://services.swpc.noaa.gov/text/discussion.txt -dump")
        elif selected == 2:
                os.system("/usr/bin/w3m https://services.swpc.noaa.gov/text/3-day-forecast.txt -dump")
        elif selected == 3:
                os.system("/usr/bin/w3m https://services.swpc.noaa.gov/text/3-day-geomag-forecast.txt -dump")
        elif selected == 4:
                os.system("/usr/bin/w3m https://services.swpc.noaa.gov/text/3-day-solar-geomag-predictions.txt -dump")
        elif selected == 5:
                os.system("/usr/bin/w3m https://services.swpc.noaa.gov/text/advisory-outlook.txt -dump")
        elif selected == 6:
                os.system("/usr/bin/w3m https://services.swpc.noaa.gov/text/weekly.txt -dump")
        elif selected == 7:
                os.system("/usr/bin/w3m https://services.swpc.noaa.gov/text/wwv.txt -dump")
        elif selected == 9:
                print (about)
        elif selected == 0:
                print ("\nExiting...\n")
                exit()          
