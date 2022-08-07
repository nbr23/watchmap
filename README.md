# WatchMap

Forked from [Bunnie's Watch Mapper](https://github.com/bunnie/watchmap) /
https://www.bunniestudios.com/blog/?p=5863

Plots Activities (run, walk, swim, etc) from a Garmin device's FIT file on OpenStreetMap using [folium](https://python-visualization.github.io/folium/) and [fitparse](https://github.com/dtcooper/python-fitparse/).

![screenshot][1]

![screenshot][2]

![screenshot][3]

## Supported devices

Tested with FIT files extracted from a Garmin Forerunner 245

## Dependencies

Works with python 3.9 and above.

## Install

`pip install watchmap`

## Retrieving FIT files

The FIT files describing your activities can be retrieved by mounting your Garming device as USB mass storage, and looking in `$MOUNTPOINT/GARMIN/Activity/*.fit`

## Usage

Simply run the tool, providing the name of the input FIT file and output HTML map:

```
usage: watchmap [-h] -i INPUT -o OUTPUT_DIR

Plot Garmin Activity on a map

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input FIT file
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        Output directory (output will be written in output_dir/{input}.html)
```

## Docker

To run watchmap through docker, use the `run_docker.sh` script:

`./run_docker.sh $INPUTFILE.FIT $OUTPUT_DIRECTORY`

[1]:docs/watchmap-01.png
[2]:docs/watchmap-02.png
[3]:docs/watchmap-03.png