'''Code to build flask app for user access and display of 
hop maps tracing an ip/web search'''


import subprocess
import socket
import ipinfo
import folium
import webbrowser
from folium.plugins import MarkerCluster
import requests
import flask
from flask import Flask, redirect, url_for, request, render_template, jsonify, send_file, Response, session
from cachelib.simple import SimpleCache
from markupsafe import Markup
import platform
from api_keys import access_token  # must contain this format: access_token = "1234567890" 
import json
import pandas as pd

import source_address



app = Flask(__name__)

# setting up the global space for cache
cache = SimpleCache()

# setting up the access token for API handling
handler = ipinfo.getHandler(access_token)

# setting up app.config for global access to map overlay
app.config["CyberRisk"] = pd.read_csv("Cyber_security.csv")



@app.route("/", methods=["GET", "POST"])
def start_trace():
    '''Starts the trace and returns the map'''
    return flask.render_template('basic_HTML_stream.html')

@app.route("/tracemyroute", methods=["POST"])
def display_hop_data():
    if request.method == "POST":
        destination = request.form.get("destination")
        if not destination:
            return "Please enter a destination.", 400
    # this will loop through the hop data and print it to the HTML page via yield
    # for that we need the destination and session data to store the global 
    # hop_list in it so the /plot_map can access it
    return Response(stream_hop_data(destination), mimetype='text/html')

def stream_hop_data(destination, source=False):

    # define max_hops
    max_hops = 30

    # get destination ip
    try:
        destination_ip = socket.gethostbyname(destination)
    # error handling to return to home page if destination is invalid
    except socket.gaierror:
        return f"Destination IP {destination} not found"

    # get source ip
    source_ip = source_address.source_address(source)

    # print traceroute command
    print(f"running traceroute on {destination} at {destination_ip} from {source_ip}")

    # to display on screen
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

        hop = output.split()

        # error handling for unresponsive hops
        if output.endswith("*\n"):
            hop_list.append({"ip": "* * *", "hostname": "N/A", "country": "N/A", 
                            "city": "N/A", "region": "N/A", "latitude": "N/A", "longitude": "N/A"})
            hop_count += 1
            max_hops -= 1
            if max_hops == 0:
                print("Max hops reached")
                break
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
            print(hop_dict)
            hop_list.append(hop_dict)

            # create a string to HTML print
            hop_str = str(hop_dict)[1:-1].replace("'", "")


            # Yield an HTML string
            yield f"{hop_count}: {hop_str}<br>" # will "print" hop data via this: Response(stream_hop_data(), mimetype='text/html')


    # At then end return a button that jumps to /plot map and uses hop_list to plot the map
    html = f'''<form action="/plot_map" method="post">
            <input type="submit" value="Plot on Map">
            </form>'''

    yield html


def get_lat_long_center(hop_list):
    lat_sum = 0
    count = 0
    lon_sum = 0
    lat_rng = [-99999, 99999]
    lon_rng = [-99999, 99999]
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

    # set zoom_start based on hop distances
    if dist <= 30:
        zoom_start = 8
    if dist <= 100:
        zoom_start = 6
    if dist <= 300:
        zoom_start = 4
    if dist <= 600:
        zoom_start = 2
    else:
        zoom_start = 4

    return lat_center, lon_center, zoom_start        

@app.route('/plot_map', methods=["GET", "POST"])
def plot_map():
    if request.method == "GET" or request.method == "POST":

        hop_list = app.config["hop_list"] 
        #print(hop_list) # used for debugging

        # info from csv on cybersecurity risk
        df = app.config["CyberRisk"]

        # pull political countries
        political_countries_url = (
            "http://geojson.xyz/naturalearth-3.3.0/ne_50m_admin_0_countries.geojson"
        )

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
            geo_data=political_countries_url,
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
            text = (f"'IP Addr:' + {str(hop["ip"])}\n"
                    f"'Location:' + {str(hop["city"])} + {str(hop["region"])} + {str(hop["country"])}\n"
                    f"'Lat/Long:' + {str(hop["latitude"])} + {str(hop["longitude"])}")

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
                

        # save map to be called by basic.html        
        map.save("templates/map.html")

        # storing results in a cache
        #cache.set('results', app.hop_list)

        return redirect(url_for('results'))
    
@app.route("/results")
def results():
    # pull hop_list
    hop_list = app.config["hop_list"]

    # render the results page template
    return render_template("results.html", tracemyroute_output=hop_list)

@app.route("/restart", methods=["POST"])
def restart_trace():
    # clear the cache
    cache.delete('results')
    # clear the hop list
    app.hop_list = []
    # clear the valid hops
    app.valid_hops = []

    return redirect("/")
    


if __name__ == "__main__":
    app.run()