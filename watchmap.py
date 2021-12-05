#! /usr/bin/env python3

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
import plotly.graph_objects as go
from jinja2 import Template


def normalize_value(varmin, varmax, value):
    return float(varmax - value) / float(varmax - varmin)

def add_to_layer(layer, pt, varname, minmax):
    norm = matplotlib.colors.Normalize(vmin=minmax[varname]['min'], vmax=minmax[varname]['max'], clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    tooltip = f"Speed: {pt.speed:0.1f}kph<br/>Heart rate: {pt.heart_rate}bpm<br/>Altitude: {pt.enhanced_altitude:0.1f}m<br/>Time: {pt.timestamp}"
    folium.CircleMarker(
        location=(pt.position_lat, pt.position_long),
        radius=10+1.5*normalize_value(minmax[varname]['min'], minmax[varname]['max'], pt[varname]),
        tooltip=tooltip,
        fill_color=matplotlib.colors.to_hex(mapper.to_rgba(pt[varname])),
        fill=True,
        fill_opacity=0.2,
        weight=0,
    ).add_to(layer)

def get_session_details(fitfile):
    session = list(fitfile.get_messages('session'))
    if len(session) != 1:
        raise Exception("Unsupported session type")
    return {
        d.name: d.value for d in session[0] if d.value is not None
    }

def plot_map(track):
    minmax = {colname: {'min': min(track[colname]), 'max': max(track[colname])} for colname in track.columns}

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
        add_to_layer(feat_group_speed, pt, 'speed', minmax)
        add_to_layer(feat_group_hr, pt, 'heart_rate', minmax)
        add_to_layer(feat_group_alt, pt, 'enhanced_altitude', minmax)

    m.add_child(feat_group_speed)
    m.add_child(feat_group_hr)
    m.add_child(feat_group_alt)
    m.add_child(folium.LayerControl())
    mapbuff = io.BytesIO()
    m.save(mapbuff, close_file=False)
    return mapbuff

def plot_charts(track):
    fig = go.Figure()
    fig.update_layout(xaxis=dict(domain=[0.05,1.0]))
    if 'enhanced_altitude' in track.columns:
        altitude_color='rgb(200, 155, 155)'
        fig.add_trace(go.Scatter(x=track['timestamp'],
                y=track['enhanced_altitude'],
                name='Altitude',
                text="Altitude (m)",
                hoverinfo='y+text',
                marker_color=altitude_color,
                ))
        fig.update_layout(yaxis1=dict(
                title='Altitude',
                titlefont=dict(color=altitude_color),
                tickfont=dict(color=altitude_color)
                ))
    if 'heart_rate' in track.columns:
        heart_rate_color='rgb(255, 50, 50)'
        fig.add_trace(go.Scatter(x=track['timestamp'],
                y=track['heart_rate'],
                name='Heart rate',
                text="Heart rate (bpm)",
                hoverinfo='y+text',
                marker_color=heart_rate_color,
                yaxis='y2'
                ))
        fig.update_layout(yaxis2=dict(
                title='Heart Rate',
                titlefont=dict(color=heart_rate_color),
                tickfont=dict(color=heart_rate_color),
                overlaying='y',
                side='left',
                anchor='free',
                position=0.0
                ))
    if 'speed' in track.columns:
        speed_color='rgb(0, 0, 109)'
        fig.add_trace(go.Scatter(x=track['timestamp'],
                y=track['speed'],
                name='Speed',
                text="Speed (km/h)",
                hoverinfo='y+text',
                marker_color=speed_color,
                yaxis='y3'
                ))
        fig.update_layout(yaxis3=dict(
                title='Speed',
                titlefont=dict(color=speed_color),
                tickfont=dict(color=speed_color),
                overlaying='y',
                side='right',
                anchor='x'
                ))
    chartsbuff = io.StringIO()
    fig.write_html(chartsbuff, full_html=False, default_height="700px")
    return chartsbuff

def build_html(fitfile, output, map=True):
    track = fitrecords_to_track(fitfile.get_messages('record'))
    mapbuff = None

    if 'position_long' not in track.columns:
        map = False

    if map:
        mapbuff = plot_map(track)
    chartsbuff = plot_charts(track)
    track_duration = track.iloc[-1].timestamp - track.iloc[0].timestamp

    session_info = get_session_details(fitfile)

    tpl = Template('''
<!DOCTYPE html>
<html style="width: 100%; height: 100%; margin: 0; padding: 0">
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
        <meta charset="UTF-8">
        <title>{{ session_info.get('sport', '').capitalize() }} - {{ session_info.start_time }}</title>
    </head>
    <body style="width: 100%; height: 100%; margin: 0; padding: 0">
        <div style="display: flex; width: 100%; height: 100%; flex-direction: column; overflow: hidden;">
            <div>
                <center>
                    <h1>{{ session_info.get('sport', '').capitalize() }} - {{ session_info.start_time }}</h1><br/>
                </center>
                <ul class="nav nav-tabs" role="tablist">
                    {% if map_iframe %}
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="mapplot-tab" data-bs-toggle="tab" data-bs-target="#mapplot" type="button" role="tab" aria-controls="mapplot" aria-selected="true">Map</button>
                    </li>
                    {% endif %}
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="detail-tab" data-bs-toggle="tab" data-bs-target="#detail" type="button" role="tab" aria-controls="detail" aria-selected="false">Detail</button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="charts-tab" data-bs-toggle="tab" data-bs-target="#charts" type="button" role="tab" aria-controls="charts" aria-selected="false">Charts</button>
                    </li>
                </ul>
            </div>
            <div class="tab-content" style="flex-grow: 1; border: none; margin: 0; padding: 0;">
                {% if map_iframe %}
                <div class="tab-pane fade show active" id="mapplot" role="tabpanel" aria-labelledby="mapplot-tab" style="width: 100%; height: 100%;">
                    <iframe id="mapplot" style="width: 100%; height: 100%;" srcdoc="{{ map_iframe }}"></iframe>
                </div>
                {% endif %}
                <div class="tab-pane fade" id="detail" role="tabpanel" aria-labelledby="detail-tab" style="width: 100%; height: 100%;">
                    <center>
                        <b>{{ session_info.get('sport', '').capitalize() }} - {{ session_info.start_time }}</b><br/>
                        Duration: {{ track_duration }}<br/>
                        Length: {{ ((session_info.total_distance / 10) | int) / 100 }}km<br/>
                        Average heart rate: {{ session_info.avg_heart_rate }}bpm<br/>
                        Average speed: {{ ((session_info.enhanced_avg_speed * 3.6 * 100) | int) / 100 }}km/h<br/>
                        Top speed: {{ ((session_info.enhanced_max_speed * 3.6  * 100) | int) / 100}}km/h<br/>
                        Total calories: {{ session_info.total_calories }}kcal<br/>
                    </center>
                </div>
                <div class="tab-pane fade show active" id="charts" role="tabpanel" aria-labelledby="charts-tab" style="width: 100%; height: 100%;">
                    {{ charts_iframe }}
                </div>
            </div>
        </div>
    </body>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p" crossorigin="anonymous"></script>
</html>''')

    with open(output, "w") as f:
        f.write(tpl.render(**{
                'track_duration': track_duration,
                'map_iframe': mapbuff.getvalue().decode('utf-8').replace('"', '&quot;') if mapbuff else None,
                'charts_iframe': chartsbuff.getvalue(),
                'session_info': session_info,
            }))

def fitrecords_to_track(fitrecords):
    track = []
    for record in fitrecords:
        track.append({
            d.name: d.value for d in record
        })
    df = pd.DataFrame(track)
    df['speed'] = df.enhanced_speed * 3.6
    if 'position_long' in df.columns and 'position_lat' in df.columns:
        df['position_long'] = df['position_long'] * 180 / math.pow(2, 31)
        df['position_lat'] = df['position_lat'] * 180 / math.pow(2, 31)
        return df.dropna(subset=['position_long', 'position_lat'])
    return df


def main():
    parser = argparse.ArgumentParser(description="Plot Garmin Activity on a map")
    parser.add_argument("-i", "--input", help="Input FIT file", required=True, type=str)
    parser.add_argument("-o", "--output_dir", help="Output directory (output will be written in output_dir/{input}.html)", type=str, required=True)
    args = parser.parse_args()

    fitfile = fitparse.FitFile(args.input)

    output = f"{args.output_dir}/{'.'.join(args.input.split('/')[-1].split('.')[:-1])}.html"

    build_html(fitfile, output)

if __name__ == "__main__":
    main()
