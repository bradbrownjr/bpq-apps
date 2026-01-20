#!/usr/bin/env python3
"""
Weather Reports for Southern Maine and New Hampshire  
----------------------------------------------------
Local weather reports from National Weather Service Gray Office.

Author: Brad Brown KC1JMH
Version: 1.2
Date: January 2026
"""

import requests

print("WX-ME v1.2 - Maine/NH Weather Reports")
print("-" * 40)

menu = """
Main Menu:
----------------------------------------
1) Maine/New Hampshire Weather Summary
2) Maine/New Hampshire Weather Roundup  
3) Western Maine/New Hampshire Forecast
4) Northern and Eastern Maine Forecast
5) Maine/New Hampshire Max/Min Temperature
   and Precipitation Table
----------------------------------------"""

about = """
Get text products right from the
National Weather Service in Gray, ME.

This is a Python3 script which pulls data from
https://www.maine.gov/mema/weather/general-information

Script developed by Brad Brown KC1JMH
"""

def pullthis(url):
        response = requests.get(url)
        data = response.text
        print("\n{}\n".format(data))

print (menu)
while True:
        selected = str(input("Menu: [1-5] R)elist A)bout Q)uit :> "))
        if "1" in selected:
                pullthis("https://tgftp.nws.noaa.gov/data/raw/aw/awus81.kgyx.rws.gyx.txt")
        elif "2" in selected:
                pullthis("https://tgftp.nws.noaa.gov/data/raw/as/asus41.kgyx.rwr.gyx.txt")
        elif "3" in selected:
                pullthis("https://tgftp.nws.noaa.gov/data/forecasts/state/nh/nhz010.txt")
        elif "4" in selected:
                pullthis("https://tgftp.nws.noaa.gov/data/raw/fp/fpus61.kcar.sft.car.txt")
        elif "5" in selected:
                pullthis("https://tgftp.nws.noaa.gov/data/raw/as/asus61.kgyx.rtp.gyx.txt")
        elif "a" in selected.lower():
                print (about)
        elif "r" in selected.lower():
                print (menu)
        elif "q" in selected.lower():
                print("\nExiting...")
                exit()
