#! /usr/bin/env python3

import os.path
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
from plotly.subplots import make_subplots
from jinja2 import Template
import base64
import logging
import importlib.metadata

AVAILABLE_METRICS = {
    "enhanced_altitude": {
        "color": "rgb(200, 155, 155)",
        "pretty_name": "Altitude",
        "unit": "m"
    },
    "heart_rate": {
        "color": "rgb(255, 50, 50)",
        "pretty_name": "Heart rate",
        "unit": "bpm"
    },
    "speed": {
        "color": "rgb(0, 0, 109)",
        "pretty_name": "Speed",
        "unit": "km/h"
    }
}

HTML_TEMPLATE_FNAME = "templates/activity.html"

logger = logging.getLogger("watchmap")
logger.addHandler(logging.StreamHandler())

def normalize_value(varmin, varmax, value):
    return float(varmax - value) / float(varmax - varmin)


def add_to_layer(layer, pt, varname, minmax):
    norm = matplotlib.colors.Normalize(
        vmin=minmax[varname]["min"], vmax=minmax[varname]["max"], clip=True
    )
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    tooltip = f"Speed: {pt.speed:0.1f}kph<br/>Heart rate: {pt.heart_rate}bpm<br/>Altitude: {pt.enhanced_altitude:0.1f}m<br/>Time: {pt.timestamp}"
    folium.CircleMarker(
        location=(pt.position_lat, pt.position_long),
        radius=10 + 1.5 * normalize_value(minmax[varname]["min"], minmax[varname]["max"], pt[varname]),
        tooltip=tooltip,
        fill_color=matplotlib.colors.to_hex(mapper.to_rgba(pt[varname])),
        fill=True,
        fill_opacity=0.2,
        weight=0,
    ).add_to(layer)


def get_session_details(fitfile):
    session = list(fitfile.get_messages("session"))
    if len(session) != 1:
        raise Exception("Unsupported session type")
    return {d.name: d.value for d in session[0] if d.value is not None}


def plot_map(track):
    minmax = {
        colname: {"min": min(track[colname]), "max": max(track[colname])}
        for colname in track.columns if len(track[colname].dropna())
    }

    m = folium.Map(
        location=[track["position_lat"].mean(), track["position_long"].mean()],
        zoom_start=15,
    )
    track_duration = track.iloc[-1].timestamp - track.iloc[0].timestamp

    feat_group_speed = folium.FeatureGroup(name="Speed")
    feat_group_hr = folium.FeatureGroup(name="Heart Rate", show=False)
    feat_group_alt = folium.FeatureGroup(name="Altitude", show=False)

    folium.Marker(
        [track.iloc[0]["position_lat"], track.iloc[0]["position_long"]],
        tooltip=f"Start<br/>Time: {track.iloc[0].timestamp}",
        icon=folium.Icon(icon="home", color="green"),
    ).add_to(m)
    folium.Marker(
        [track.iloc[-1]["position_lat"], track.iloc[-1]["position_long"]],
        tooltip=f"End<br/>Length: {track.iloc[-1].distance/1000:0.1f}km<br/>Duration: {track_duration}<br/>Time: {track.iloc[-1].timestamp}",
        icon=folium.Icon(icon="flag", color="red"),
    ).add_to(m)

    for _, pt in track.iterrows():
        if pt.speed == 0:
            pt.speed = 0.01
        add_to_layer(feat_group_speed, pt, "speed", minmax)
        add_to_layer(feat_group_hr, pt, "heart_rate", minmax)
        add_to_layer(feat_group_alt, pt, "enhanced_altitude", minmax)

    m.add_child(feat_group_speed)
    m.add_child(feat_group_hr)
    m.add_child(feat_group_alt)
    m.add_child(folium.LayerControl())
    mapbuff = io.BytesIO()
    m.save(mapbuff, close_file=False)
    return mapbuff


def plot_charts(track):
    metrics = sorted(list(set(AVAILABLE_METRICS).intersection(set(track.columns))))
    nb_rows = len(metrics)
    fig = make_subplots(rows=nb_rows, cols=1)
    current_row = 1

    for metric in metrics:
        fig.add_trace(
            go.Scatter(
                x=track["timestamp"],
                y=track[metric],
                name=AVAILABLE_METRICS[metric]["pretty_name"],
                text="{pretty_name} ({unit})".format(**AVAILABLE_METRICS[metric]),
                hoverinfo="y+text",
                marker_color=AVAILABLE_METRICS[metric]["color"],
            ),
            row=current_row,
            col=1,
        )
        current_row += 1
    chartsbuff = io.StringIO()
    fig.write_html(chartsbuff, full_html=False, default_height="700px", default_width="100%")
    return chartsbuff

def build_html(input_path, output, map=True, embed_fit=False):
    fitfile = fitparse.FitFile(input_path)
    track = fitrecords_to_track(fitfile.get_messages("record"))
    mapbuff = None
    b64fit = None

    if embed_fit:
        with open(input_path, "rb") as input_file:
            b64fit = os.path.basename(input_path), base64.b64encode(input_file.read()).decode('utf-8')

    if "position_long" not in track.columns:
        logger.warn("No GPS coordinates found in the FIT file, not plotting the map")
        map = False

    if map:
        mapbuff = plot_map(track)
    chartsbuff = plot_charts(track)
    track_duration = track.iloc[-1].timestamp - track.iloc[0].timestamp

    session_info = get_session_details(fitfile)

    with open(os.path.join(os.path.dirname(__file__), HTML_TEMPLATE_FNAME), "r") as html_template:
        tpl = Template(html_template.read())

    with open(output, "w") as f:
        f.write(
            tpl.render(
                **{
                    "track_duration": track_duration,
                    "map_iframe": mapbuff.getvalue()
                    .decode("utf-8")
                    .replace('"', "&quot;")
                    if mapbuff
                    else None,
                    "charts_iframe": chartsbuff.getvalue(),
                    "session_info": session_info,
                    "fit_file": b64fit,
                }
            )
        )
        logger.info("Output written to %s" % output)


def fitrecords_to_track(fitrecords):
    track = []
    for record in fitrecords:
        track.append({d.name: d.value for d in record})
    df = pd.DataFrame(track)
    if 'enhanced_speed' in df.columns:
        df["speed"] = df.enhanced_speed * 3.6
    if "position_long" in df.columns and "position_lat" in df.columns:
        df["position_long"] = df["position_long"] * 180 / math.pow(2, 31)
        df["position_lat"] = df["position_lat"] * 180 / math.pow(2, 31)
        return df.dropna(subset=["position_long", "position_lat"])
    return df


def run():
    parser = argparse.ArgumentParser(description="Plot Garmin Activity on a map")
    parser.add_argument("-i", "--input", help="Input FIT file", required=True, type=str)
    parser.add_argument(
        "-o",
        "--output_dir",
        help="Output directory (output will be written in output_dir/{input}.html)",
        type=str,
        required=True,
    )
    parser.add_argument("-v", "--verbose", action='store_true')
    parser.add_argument("-V", "--version", action='version', version=f"watchmap v{importlib.metadata.version('watchmap')}")
    parser.add_argument("-f", "--force", help="Overwrite output file if it exists", action='store_true')
    parser.add_argument("--embed-fit", dest="embed_fit", help="Embed FIT file into the generated HTML page", action='store_true')
    args = parser.parse_args()

    if args.verbose:
        print(f"watchmap v{importlib.metadata.version('watchmap')}")
        logger.setLevel(logging.INFO)

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    output = os.path.join(args.output_dir, f"{'.'.join(args.input.split('/')[-1].split('.')[:-1])}.html")

    logger.info(f"Processing {args.input}")

    if os.path.exists(output) and not args.force:
        logger.warn(f"Output file '{output}' already exists, skipping.")
        return

    build_html(args.input, output, embed_fit=args.embed_fit)

