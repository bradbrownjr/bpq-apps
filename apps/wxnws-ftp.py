# Variables
region = "gyx" # Lowercase region code for local NWS office

# Enable use of FTP with Python
import ftplib

# Define the FTP server and credentials
ftp = ftplib.FTP('tgftp.nws.noaa.gov')
ftp.login()

# Define the directory to change to
ftp.cwd('data/raw/fx')

# Find files fxus[##].kgyx.afd.gyx.txt and download them
files = ftp.nlst('fxus*.afd.$region.txt')
for file in files:
    with open(file, 'wb') as f:
        ftp.retrbinary('RETR ' + file, f.write)

# Display the files downloaded, pausing for input on every line containging "&&" to continue or quit
for file in files:
    with open(file, 'r') as f:
        for line in f:
            print(line)
            if "&&" in line:
                # Input "press enter to continue or Q to quit"
                user_input = input("Press Enter to continue or Q to quit...")
                if user_input.lower() == "q":
                    exit()
            elif "&&" not in line:
                continue
            else:
                break
