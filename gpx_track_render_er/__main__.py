import confuse
from datetime import datetime as dt
from faker import Faker
from geopy import distance
import gpxpy
import gpxpy.gpx
import logging
import srtm
import isodate
import urllib.parse


def guess_timestamp_with_acc(timestamp: str, accuracy: str = "PT0H0M0S") -> dt:
    dt_format = "%Y-%m-%dT%H:%M:%S%z"  # 2020-12-29T13:34:38+00:00
    acc_span = isodate.parse_duration(accuracy)
    start_time = dt.strptime(timestamp, dt_format) - acc_span
    end_time = dt.strptime(timestamp, dt_format) + acc_span

    fake = Faker()
    return fake.date_time_between_dates(start_time, end_time)


def main():
    logging.debug("Importing configuration data")
    config = confuse.Configuration("gpx_track_render_er", __name__)
    config.set_file("config_default.yaml")

    start_time = guess_timestamp_with_acc(
        config["start"]["time"]["timestamp"].get(str),
        config["start"]["time"]["accuracy"].get(str),
    )
    finish_time = guess_timestamp_with_acc(
        config["finish"]["time"]["timestamp"].get(str),
        config["finish"]["time"]["accuracy"].get(str),
    )

    elevation_data = srtm.get_data()

    finish_location = (
        config["finish"]["location"]["lat"].get(),
        config["finish"]["location"]["lon"].get(),
    )
    finish_elevation = elevation_data.get_elevation(
        finish_location[0], finish_location[1]
    )
    finish_location = gpxpy.gpx.GPXTrackPoint(
        latitude=finish_location[0],
        longitude=finish_location[1],
        elevation=finish_elevation,
    )

    gpx = gpxpy.parse(open(config["gpx_file"]["filename"].as_filename(), "r"))
    track = next(
        (x for x in gpx.tracks if x.name == config["gpx_file"]["track_name"].get(str)),
        None,
    )

    print("Processing track name {0}".format(track.name))
    nearest_location = track.segments[0].points[0]
    shortest_dist = distance.distance(meters=float("inf"))
    for segment in track.segments:
        for point in segment.points:
            this_distance = distance.distance(
                (finish_location.latitude, finish_location.longitude),
                (point.latitude, point.longitude),
            )

            print("Distance from finish: {0}".format(this_distance))

            if this_distance < shortest_dist:
                shortest_dist = this_distance
                nearest_location = point

    print(
        "Estimated finish at {0}. Closest GPX track point is ({1},{2}) -> {3} metres away from the finish location".format(
            finish_time,
            nearest_location.latitude,
            nearest_location.longitude,
            round(shortest_dist.m, 2),
        )
    )
    gmaps_params = urllib.parse.urlencode(
        {
            "api": 1,
            "basemap": "terrain",
            "origin": (finish_location.latitude, finish_location.longitude),
            "destination": (nearest_location.latitude, nearest_location.longitude),
        }
    )
    print("View at : https://www.google.com/maps/dir/?{0}".format(gmaps_params))

    gpx_output = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_output.tracks.append(gpx_track)


if __name__ == "__main__":
    # execute only if run as a script
    main()
