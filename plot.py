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


def speed_conversion(raw):
    return 3.6*raw # convert m/s to km/h

def plot_osm_map(track, output='speed-map.html', hr=None):
    speeds = track['speed']
    minima = min(speeds)
    maxima = max(speeds)

    norm = matplotlib.colors.Normalize(vmin=minima, vmax=maxima, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    m = folium.Map(location=[track.iloc[0]['position_lat'], track.iloc[0]['position_long']], zoom_start=15)
    for _, pt in track.iterrows():
        if pt.speed == 0:
            pt.speed = 0.01

        tooltip = f"Speed: {pt.speed:0.1f}kph<br/>Heart rate: {pt.heart_rate}bpm<br/>Altitude: {pt.enhanced_altitude:0.1f}m"
        folium.CircleMarker(
            location=(pt.position_lat, pt.position_long),
            radius=pt.speed**2 / 8,
            tooltip=tooltip,
            fill_color=matplotlib.colors.to_hex(mapper.to_rgba(pt.speed)),
            fill=True,
            fill_opacity=0.2,
            weight=0,
        ).add_to(m)

    m.save(output)

def plot_osm_hr_map(track, hr_file, output='hr-map.html', age=45, resting_rate=50, hr_plot_interval=30):
    # speeds will have already been adjusted since we side-effect the global record
#    for i in range(len(track['speed'])):
#        track['speed'][i] = speed_conversion(track['speed'][i])

    maxrate = 220-age
    reserve = maxrate-resting_rate
    rate_table = {
       'resting  ' : [(0.0*reserve + resting_rate, 0.5*reserve + resting_rate), 0],
       'easy     ' : [(0.5*reserve + resting_rate, 0.6*reserve + resting_rate), 0],
       'fatburn  ' : [(0.6*reserve + resting_rate, 0.70*reserve + resting_rate), 0],
       'cardio   ' : [(0.70*reserve + resting_rate, 0.80*reserve + resting_rate), 0],
       'sprint   ' : [(0.80*reserve + resting_rate, 0.90*reserve + resting_rate), 0],
       'anaerobic' : [(0.9*reserve + resting_rate, 1.0*reserve + resting_rate), 0],
    }

    hr = hr_file['hr']
    times = track['time']
    datetimes = []
    for t in times:
        datetimes.append(datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ'))

    totaltime = (datetimes[-1] - datetimes[0]).total_seconds()

    for i in range(0,len(datetimes) - 1):
        cur_hr = hr[i]
        for name, entry in rate_table.items():
            (hrmin, hrmax) = entry[0]
            if hrmin < cur_hr and cur_hr <= hrmax:
                entry[1] += (datetimes[i+1] - datetimes[i]).total_seconds()

    cum_time = 0 # this is different, because fractional seconds are lost every reading and eventually creates a 2x error!
    for name, entry in rate_table.items():
        cum_time += entry[1]

    for name, entry in rate_table.items():
        (hrmin, hrmax) = entry[0]
        print(name + ' ({:3.0f}-{:3.0f}): '.format(hrmin, hrmax) + str(timedelta(seconds= (entry[1] / cum_time) * totaltime)).split('.')[0] + ' {:.1f}'.format(100.0 * (entry[1] / cum_time)) + '%')

    speeds = track['speed']
    minima = min(speeds)
    maxima = max(speeds)

    norm = matplotlib.colors.Normalize(vmin=minima, vmax=maxima, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.plasma)
    m = folium.Map(location=[track['lat'][0], track['lon'][0]], zoom_start=15)
    elapsed = 0.0
    cur_interval = 0.0
    hr_avg_sum = 0.0
    hr_n = 0
    for index in range(len(hr) - 1):
        elapsed += ( datetime.strptime(track['time'][index+1], '%Y-%m-%dT%H:%M:%SZ') - datetime.strptime(track['time'][index], '%Y-%m-%dT%H:%M:%SZ') ).total_seconds()
        hr_avg_sum += hr[index]
        hr_n += 1
        if elapsed >= cur_interval:
            cur_interval += hr_plot_interval
            folium.map.Marker(
                [track['lat'][index], track['lon'][index]],
                icon=DivIcon(
                    icon_size=(60,12),
                    icon_anchor=(0,0),
                    html='<div style="font-size: 10pt">'+'{:.0f}'.format(hr_avg_sum / hr_n)+'</div>',
                )
            ).add_to(m)
            hr_avg_sum = 0.0
            hr_n = 0

        if track['speed'][index] == 0:
            track['speed'][index] = 0.01

        if hr:
            tooltip="{:0.1f}kph".format(track['speed'][index]) + ' ' + str(hr[index]) +'bpm'
        else:
            tooltip="{:0.1f}kph".format(track['speed'][index])
        folium.CircleMarker(
            location=(track['lat'][index], track['lon'][index]),
            radius=((hr[index] - minima) / 50.0)**2,
            tooltip=tooltip,
            fill_color=matplotlib.colors.to_hex(mapper.to_rgba(speeds[index])),
            fill=True,
            fill_opacity=0.2,
            weight=0,
        ).add_to(m)

    m.save(output)

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
    return df


def main():
    parser = argparse.ArgumentParser(description="Plot Garmin Activity on a map")
    parser.add_argument("-i", "--input", help="Input file", required=True, type=str)
    parser.add_argument("-o", "--output", help="HTML output map file name (defaults to {input}.html", type=str)
    args = parser.parse_args()

    fitfile = fitparse.FitFile(args.input)
    if args.output is None:
        args.output = f"{''.join(args.input.split('.')[:-1])}.html"

    track = fitrecords_to_track(fitfile.get_messages('record'))
    plot_osm_map(track, args.output)

if __name__ == "__main__":
    main()
