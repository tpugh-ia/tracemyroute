'''
Start here. 
The starting place and main landing point for tracemyroute.
Code is currently ran and displayed using a development server.
Code includes build flask app for user to access begin_tracemyroute.html. 
The user input desintation URL is validated through dest_address.py and source address is discovered through source_address.py.
Hops are streamed to /tracemyroute to show app is working and to track progress.
Code builds folium map working with json and chloropleth for display features.
Results are yielded through tracemyroute_results.html.
Any errors are yielded through tracemyroute_error.html.

Notes are included for running code on a web browser, but requires permissions that have not been debugged.
'''

# import necessary libraries
import subprocess
import socket
import ipinfo
import folium
import webbrowser
from folium.plugins import MarkerCluster
import requests
import flask
from flask import Flask, redirect, url_for, request, render_template, jsonify, send_file, Response, session, stream_with_context
from cachelib.simple import SimpleCache
from markupsafe import Markup
import platform
import json
import pandas as pd
import os
import sys
import datetime

# import from root folder
import source_address
import dest_address
from api_keys import access_token  # must contain this format: access_token = "1234567890" 

#
# pythonanywhere deployment:

# change from /home/<user> to /home/<user>/mysite
# adjust mysite to your project root!
# Check if running on PythonAnywhere
if 'PYTHONANYWHERE_SITE' in os.environ:
    os.chdir("tracemyroute")
    print("working folder is", os.getcwd(), file=sys.stderr)


# setting up the environment
app = Flask(__name__)

# setting up the global space for cache
cache = SimpleCache()


# Access token for API handling

# ACTIVATE for INTERNAL CONFIGURATION use
handler = ipinfo.getHandler(access_token)

# ACTIVATE for WEB PLATFORM use
#handler = os.environ.get('access_token')   # for grabbing access_token from Render environment


# setting up app.config for global access to map overlay
app.config["CyberRisk"] = pd.read_csv("Cyber_security.csv")
app.config["counties"] = "countries.geojson" # for political countries


# beginning code
@app.route("/", methods=["GET", "POST"])
def start_trace():
    '''Starts the trace and returns the map'''
    return flask.render_template('begin_tracemyroute.html')

@app.route("/tracemyroute", methods=["POST"])
def display_hop_data():
    '''Displays the hop data, streaming each hop in the browser until traceroute is complete.
    Includes error handling for invalid destinations.'''

    if request.method == "POST":
        # get destination input from begin_tracemyroute.html form
        destination = request.form.get("destination")

        # validate destination ip
        result, message = dest_address.dest_address(destination)
        if result == False:
            return redirect(url_for("error", error_message=message))
        else:
            response = Response(stream_hop_data(destination), mimetype='text/html')
            response.headers['X-Accel-Buffering'] = 'no' # needed for nginx (pythonanywhere)
            return response

def stream_hop_data(destination, source=False):
    '''Stream hop data. Starting with displaying destination url/IP address and source IP address.
    Each hop displays IP address, hostname, city/state/country/post code, latitutde/longitude, if available.
    If no data is available "* * *" is displayed.
    Each hop is added to hop_list.
    
    Args:
        destination: destination URL is user input from html form
    
    Returns:
        streamed hop data
        button to plot map
    '''

    # get destination ip
    destination_ip = socket.gethostbyname(destination)

    # get source ip
    source_ip = source_address.source_address(source)

    # display traceroute request
    #print(f"running traceroute on {destination} at {destination_ip} from {source_ip}") # for debugging
    yield f"Running traceroute on {destination} at {destination_ip} from {source_ip}<br><br>"

    # setting initial hop count
    hop_count = 0
    
    # create hop empty hop list for IP addresses as a key in session
    hop_list = app.config["hop_list"] = []

    # define traceroute
    if platform.system() == "Windows":
        traceroute = subprocess.Popen(["tracert", "-w", "10", destination], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT,
                                    text=True)
    else:
        traceroute = subprocess.Popen(["traceroute", "-w", "10", destination], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT,
                                    text=True)
                                    
    first_line = True

    while True:
        # get output from traceroute
        output = traceroute.stdout.readline()
        if not output:
            break # no more output
        
        # skip anything starting with traceroute as not hop
        if output.startswith("traceroute") or output.startswith("Tracing") or output.startswith("over"):
            continue

        # error handling for unresponsive hops
        if output.endswith("*\n"):
            hop_list.append({"ip": "* * *", "hostname": "N/A", "country": "N/A", 
                            "city": "N/A", "region": "N/A", "latitude": "N/A", "longitude": "N/A"})
            hop_count += 1
            yield f"{hop_count}: * * *<br>\n"
            
        else: 
            # reviewing hop details
            for tok in output.split():
                if tok.endswith(")") or tok.endswith("]"): # find token ending in )
                    ip = tok[1:-1] # remove ()s or []s
                    break
            else:
                continue 

            hop_details = handler.getDetails(ip)
            hop_count += 1
            hop_dict = {}

            for key in ["ip", "hostname", "country", "city", "region", "latitude", "longitude"]:
                if key in hop_details.all:
                    hop_dict[key] = hop_details.all[key]
                else:
                    hop_dict[key] = "N/A"
            #print(hop_dict)    # for debugging
            hop_list.append(hop_dict)

            # create a string to HTML print
            hop_str = str(hop_dict)[1:-1].replace("'", "")


            # Yield an HTML string
            # will "print" hop data via this: Response(stream_hop_data(), mimetype='text/html')
            yield f"{hop_count}: {hop_str}<br>\n"
    

    # At then end return a button that jumps to /plot map and uses hop_list to plot the map
    html = f'''<form action="/plot_map" method="post">
            <input type="submit" value="Plot on Map">
            </form>'''

    yield html

def get_lat_long_center(hop_list):
    '''Defines folium map's center based on the hop_list results
    
    Args:
        hop_list: populated from stream_hop_data
    
    Returns:
        lat_center, lon_center, and zoom_start for building the plot map
    '''
    
    lat_sum = 0
    count = 0
    lon_sum = 0
    lat_rng = [-99999, 99999]
    lon_rng = [-99999, 99999]

    lat_center = 0
    lon_center = 0

    for hop in hop_list:
        if hop["latitude"] != "N/A":
            lat_sum += float(hop["latitude"])
            lon_sum += float(hop["longitude"])
            count += 1

            lat_rng[0] = max(float(hop["latitude"]), lat_rng[0])
            lat_rng[1] = min(float(hop["latitude"]), lat_rng[1])    
            lon_rng[0] = max(float(hop["longitude"]), lon_rng[0])
            lon_rng[1] = min(float(hop["longitude"]), lon_rng[1])

            lat_center = lat_sum / count
            lon_center = lon_sum / count

    # get distance of half of diagonal of bounding box
    lat_dist = lat_rng[0] - lat_rng[1]
    lon_dist = lon_rng[0] - lon_rng[1]
    dist = ((lat_dist**2 + lon_dist**2)**0.5 / 2) * 100 # in km

    # set zoom_start based on distances between farthest hops
    if dist <= 30:
        zoom_start = 8
    if dist <= 100:
        zoom_start = 6
    if dist <= 300:
        zoom_start = 4
    if dist <= 600:
        zoom_start = 2
    if dist <= 1000:
        zoom_start = 0.5
    else:
        zoom_start = 6

    return lat_center, lon_center, zoom_start        

@app.route('/plot_map', methods=["POST"])
def plot_map():
    '''Based on the hop_list, a map is plotted with markers, 
    lusters indicating multiple hops in one location, and a line connecting the hops.
    The map is saved in /templates/ with a timestamp, and if any previous map exists, it is removed.
    The map is displayed in /results.'''

    if request.method == "POST":

        hop_list = app.config["hop_list"] 
        #print(hop_list) # for debugging

        # info from csv on cybersecurity risk
        df = app.config["CyberRisk"]

        # setting up zoom/base for map
        center_lat, center_lon, zoom_start = get_lat_long_center(hop_list)

        # basemap, starting point
        map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles= "cartodb positron",
        )  

        # cyber_security risk level overlay
        folium.Choropleth(
            geo_data=app.config["counties"],
            data=df,
            columns=("Country", "CEI"),
            key_on="feature.properties.name",
            fill_color="RdYlGn_r",
            fill_opacity=0.8,
            line_opacity=0.2,
            nan_fill_color="white",
            legend_name="Cyber Security Risk",
        ).add_to(map) 

        marker_cluster = MarkerCluster().add_to(map)

        # creating an empty valid_hops list to call valid locations for drawing the map
        valid_hops = []

        # add markers for each hop to the map
        for hop in hop_list:

            # define text at each marker
            text = (f"{str(hop['ip'])}<br>"
                    f"{str(hop['city'])}, {str(hop['region'])}, {str(hop['country'])}<br>"
                    f"{str(hop['latitude'])}, {str(hop['longitude'])}")

            # setting up an if loop to identify hops with IP/Geo info
            if hop["ip"] != "* * *" and hop["latitude"] != "N/A":
                lat = float(hop["latitude"])
                lon = float(hop["longitude"])
                valid_hops.append([lat, lon])

                # plot mop
                folium.CircleMarker(
                    location=[hop["latitude"], hop["longitude"]],
                    radius=5, # circle size
                    popup=text, # text at marker
                    color= "#00FFFF", # cyan/aqua
                    width= 1,
                    fill= True, # fill marker with fill_color
                    fill_color= "#00FFFF", # set same as color, cyan/aqua
                    fill_opacity= 0.9 # set opacity 90% opacity = 10% transparent
                    ).add_to(marker_cluster)
                
                folium.PolyLine(valid_hops,
                            color= "#0000000",
                            weight= 3,
                            opacity= 0.9).add_to(map)

        # add layer control to map
        folium.LayerControl().add_to(map)

        # draw lines between hops
        if len(valid_hops) > 1:
            # setting count for for loop
            count = 0

            # for loop to create lines between hops
            for hops in valid_hops:
                if count < len(valid_hops) - 1:
                    folium.PolyLine([valid_hops[count], valid_hops[count + 1]],
                                    color= "#000000",
                                    weight= 3,
                                    opacity= 0.9).add_to(map)
                    count += 1
                

        # save map to be called by results.html with unique version
        timestamp = int(datetime.datetime.now().timestamp())
        map_file_name = f"templates/map_{timestamp}.html"       
        map.save(map_file_name)

        # delete any previous version of map.html
        for file in os.listdir("templates"):
            if file.startswith("map_") and file != os.path.basename(map_file_name):
                os.remove(os.path.join("templates", file))

        #return redirect(url_for('results', reload_map=True))
        return redirect(url_for('results', map=f"map_{timestamp}.html"))

@app.route("/results/<map>")
def results(map):
    '''Display final traceroute hop list, folium map, and an option to begin tracemyroute again.
    tracemyroute_results.html is called.
    
    Args:
        map: the plotted folium map is used to build the results page
    
    Returns: 
        template for tracemyroute_results to display folium map, traceroute hop list, 
        and simple form to begin a traceroute again.
    '''

    # pull hop_list
    hop_list = app.config["hop_list"]

    # to account for no hops
    if len(hop_list) == 0:
        return redirect(url_for('error', error_message="Hops cannot be determined."))

    # render the results page template#
    return render_template("tracemyroute_results.html", tracemyroute_output=hop_list, map=map)

@app.route("/restart", methods=["POST"])
def restart_trace():
    '''When the user decide to start trace again, this code is called to delete cache, 
    delete any current values in hop_list and valid_hops, and a new destination is grabbed from the html form.
    The code then displays new hop data in an html stream.'''

    # clear the cache
    cache.delete('results')
    # clear the hop list
    app.config["hop_list"] = []
    # clear the valid hops
    app.config["valid_hops"] = []

    # pulling destination from form input
    destination = request.form.get("destination")

    # error handling for invalid inputs
    result, message = dest_address.dest_address(destination)
    if result == False:
        return redirect(url_for("error", error_message=message))
    else:
        return Response(stream_hop_data(destination), mimetype="text/html")

    
@app.route("/error/<error_message>")
def error(error_message):
    '''Error handling for tracemyroute
    
    Args:
        error_message: string that populates the error message on the tracemyroute_error.html page
    
    Returns:
        template to display error message on tracemyroute_error.html
    '''
    return render_template("tracemyroute_error.html", error_message=error_message)

if __name__ == "__main__":
    app.run()
