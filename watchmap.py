#!/usr/bin/python3

import sys
import argparse
import fitparse
import pandas as pd
import math
import matplotlib
import matplotlib.cm as cm
import folium
from folium.features import DivIcon
from datetime import datetime, timedelta
import io


def speed_conversion(raw):
    return 3.6*raw # convert m/s to km/h

def normalize_value(varmin, varmax, value):
    return float(varmax - value) / float(varmax - varmin)

def add_to_layer(mapper, layer, pt, varname, varmin, varmax):
    tooltip = f"Speed: {pt.speed:0.1f}kph<br/>Heart rate: {pt.heart_rate}bpm<br/>Altitude: {pt.enhanced_altitude:0.1f}m"
    folium.CircleMarker(
        location=(pt.position_lat, pt.position_long),
        radius=10+1.5*normalize_value(varmin, varmax, pt[varname]),
        tooltip=tooltip,
        fill_color=matplotlib.colors.to_hex(mapper.to_rgba(normalize_value(varmin, varmax, pt[varname]), norm=False)),
        fill=True,
        fill_opacity=0.2,
        weight=0,
    ).add_to(layer)

def plot_osm_map(track, output):
    minima = min(track['speed'])
    maxima = max(track['speed'])
    min_hr = min(track['heart_rate'])
    max_hr = max(track['heart_rate'])
    min_alt = min(track['enhanced_altitude'])
    max_alt = max(track['enhanced_altitude'])

    norm = matplotlib.colors.Normalize(vmin=minima, vmax=maxima, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    m = folium.Map(location=[track['position_lat'].mean(), track['position_long'].mean()], zoom_start=15)
    track_duration = track.iloc[-1].timestamp - track.iloc[0].timestamp

    feat_group_speed = folium.FeatureGroup(name='Speed')
    feat_group_hr = folium.FeatureGroup(name='Heart Rate', show=False)
    feat_group_alt = folium.FeatureGroup(name='Altitude', show=False)

    folium.Marker([track.iloc[0]['position_lat'], track.iloc[0]['position_long']], tooltip=f"Start<br/>Time: {track.iloc[0].timestamp}",icon=folium.Icon(icon="home", color="green")).add_to(m)
    folium.Marker([track.iloc[-1]['position_lat'], track.iloc[-1]['position_long']], tooltip=f"End<br/>Length: {track.iloc[-1].distance/1000:0.1f}km<br/>Duration: {track_duration}<br/>Time: {track.iloc[-1].timestamp}", icon=folium.Icon(icon="flag", color="red")).add_to(m)

    for _, pt in track.iterrows():
        if pt.speed == 0:
            pt.speed = 0.01
        add_to_layer(mapper, feat_group_speed, pt, 'speed', minima, maxima)
        add_to_layer(mapper, feat_group_hr, pt, 'heart_rate', min_hr, max_hr)
        add_to_layer(mapper, feat_group_alt, pt, 'enhanced_altitude', min_alt, max_alt)

    m.add_child(feat_group_speed)
    m.add_child(feat_group_hr)
    m.add_child(feat_group_alt)
    m.add_child(folium.LayerControl())
    iframebuf = io.BytesIO()
    m.save(iframebuf, close_file=False)

    with open(output, "w") as f:
        f.write('''
        <!DOCTYPE html>
        <html style="width: 100%; height: 100%; margin: 0; padding: 0">
        <head>
        <meta charset="UTF-8">
        </head>
        <body style="width: 100%; height: 100%; margin: 0; padding: 0">
        <div style="display: flex; width: 100%; height: 100%; flex-direction: column; overflow: hidden;">
        <div>
        <center>
        <b>{}</b><br/>
        Duration: {}<br/>
        Length: {:0.1f}km<br/>
        </center>
        </div>
        <iframe style="flex-grow: 1; border: none; margin: 0; padding: 0; " srcdoc="{}"></iframe>
        </div>
        </body>
        </html>'''.format(
            track.iloc[0].timestamp,
            track_duration,
            track.iloc[-1].distance/1000,
            iframebuf.getvalue().decode('utf-8').replace('"', '&quot;')
            ))


def fitrecords_to_track(fitrecords):
    track = []
    for record in fitrecords:
        track.append({
            d.name: d.value for d in record
        })
    df = pd.DataFrame(track)
    df['speed'] = df.enhanced_speed * 3.6
    df['position_long'] = df['position_long'] * 180 / math.pow(2, 31)
    df['position_lat'] = df['position_lat'] * 180 / math.pow(2, 31)
    return df.dropna(subset=['position_long', 'position_lat'])


def main():
    parser = argparse.ArgumentParser(description="Plot Garmin Activity on a map")
    parser.add_argument("-i", "--input", help="Input FIT file", required=True, type=str)
    parser.add_argument("-o", "--output", help="HTML output map file name (defaults to {input}.html)", type=str)
    args = parser.parse_args()

    fitfile = fitparse.FitFile(args.input)
    if args.output is None:
        args.output = f"{'.'.join(args.input.split('.')[:-1])}.html"

    track = fitrecords_to_track(fitfile.get_messages('record'))
    plot_osm_map(track, args.output)

if __name__ == "__main__":
    main()
