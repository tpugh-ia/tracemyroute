# User Guide
## tracemyroute
584 Project - By Tiffany Elizabeth

## About
Every day we send and receive email, search for news, recipes, or directions, and browse various websites. And every time we click to search, send, or download, the results appear instantaneous but in actuality that data has taken quite a trip to get to you. Enter tracemyroute.

Tracemyroute is an interactive search engine to follow your data's journey from start to end. Every step, or what network aficionados call a "hop," has something to share: an IP address, hostname, a city, a country, postal code, or that it is sitting behind a firewall ("* * *"). These hops can provide a lot of information, especially if you are in the networking and cybersecurity world, or it can be simply interesting to watch.

So, if you are new to networking/cybersecurity, a student interested in network architecture and security practices, or just a little curious of what happens behind the scenes in the Internet world, tracemyroute is a fun tool for you.

# How it Works
It starts with a destination url. Enter the interested destination as a valid URL (or IP address) and click "Start Trace." Watch as the screen streams each hop displaying the IP address, hostname, city, state, country, post code, longitude, and latitude. If the hop does not respond or is protected behind firewalls, *** will display. Depending on firewalls and location, each trace varies in timing; hops will continue to display until the destination is reached. when the destination is reached, the user can click "Plot Map" to see the hops displayed on a map that shows the path against the backdrop of countries color-coded based on cybersecurity risk. The results also display all hop data and the option to start a new trace. If an error is encountered (i.e. invalid URL, unreachable URL, etc.) the user will be directed to an error page and given the option to try again. 

## Program Requirements
### Python Version:
Python 3.10 or higher. This is essential as certain libraries may not be available or compatible with older versions. (Note: this code was built in a python3.12 environment but also test ran on a python3.10 environment.)

### Python Libraries:
- flask
* folium
+ iPInfo - See API Requirements below for important set up information
- requests
* markupsafe
+ pandas
- cachelib
* numpy

You can install the required libraries using the following command in your terminal or command prompt accessing the requirements.txt:
##
    pip install --upgrade -r requirements.txt

In order for this program to run properly with all features activated, each of these libraries need to be installed in your python 3.10 (or higher) environment.

### API Requirements:
IpInfo is an IP Address Database that works well within the Python environment providing clean and up to date IP data. IpInfo is used in this code to pull geolocation and hostname information from each hop's IP address.

Obtaining an API Key from IpInfo is essential for this code to function. To obtain your own API key, visit [ipinfo.io](https://ipinfo.io/signup). 

Once you have your own API key, update the api_keys.py.template file, filling in the access_token with your API key (be sure to add " " around it), rename the file by removing the .template so that it can be called appropriately and also recognized by gitignore. Alternative, you can copy/paste the line below replacing "abcdefg123456" with your API key. Be sure to keep the " " around your API key.
##
    access_token = "abcdefg123456"

New to API keys? Check out [What is an API?](https://www.ibm.com/topics/api) for more information.

## How to Use
### Set up your environment:
To get started, all it takes is four quick steps:
1. Update Python environment to 3.10 or higher
2. Install all required libraries
3. Set up API key from IpInfo in a file titled api_keys.py (make sure api_keys.py is in your root folder)
4. Open main.py and run!

### When running from a terminal:
1. Download tracemyroute repository
2. Open OS terminal
3. Use cd to jump to project root folder (i.e. cd /Users/<myname>/Desktop/tracemyroute
4. Run pip install --upgrade -r requirements.txt
5. Run tracemyroute: python main.py

If you are looking to run this application on a web server, check out the [server_deploy.md](https://github.com/tiffany-elizabeth-gh/tracemyroute/blob/7abc3751f4fbfbf2991fb5bd6cf283dc896eacc9/docs/server_deploy.md).

### Running tracemyroute:
When the code is run your browser will display the starting point for tracemyroute, prompting the user to enter a destination url. Upon clicking "Start Trace" the screen will change showing the stream of hop data. When the trace is complete, a button will appear for the user to "Plot Map." Clicking this will take the user to the results page that displays three things: 1) the folium map tracing each hop (with optional clicking for more details for each hop) 2) the hop list with hop details and 3) the option to begin a new trace. 

![tracemyroute](https://github.com/user-attachments/assets/60a43b54-971f-4773-b062-528adde57054)

### Error handling:
Tracemyroute is configured to handle errors such as invalid URL entries or destinations entered that result in no recorded hops. When an error like this occurs, the user is redirected to an error page and given the option to try again.

![tracemyroute_error](https://github.com/user-attachments/assets/9555209f-09d3-4864-a2c4-69cc95c0fbe3)

## Limitations
It was the original design and goal to deploy this code in an external environment such as pythonanywhere or Render to make the tool more accessible. Certain web platforms, such as these, limit the scope of this application because of the operating system access required to complete the traceroute(s). The team was able to successfully deploy tracemyroute on pythonanywhere, and the steps can be found within the [server_deploy.md](https://github.com/tiffany-elizabeth-gh/tracemyroute/blob/7abc3751f4fbfbf2991fb5bd6cf283dc896eacc9/docs/server_deploy.md). There are still limitations with running on a free server and unknown issues to debug at this time. The server-specific deploy code can be found in the server_deploy branch.

## Acknowledgements
Thank you to Professor Harding for his guidance, assistance, continued help, and patience as this project proved to be trickier than expected. This could not have gotten to this place without him. And thank you to my 2024 cybersecurity course for the inspiration and introduction into cybersecurity.
