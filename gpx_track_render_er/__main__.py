import confuse
from datetime import datetime as dt
from faker import Faker
from geopy import distance
import gpxpy
import gpxpy.gpx
import logging
import pytz
import srtm
import isodate
import urllib.parse


def guess_timestamp_with_acc(timestamp: str, accuracy: str = "PT0H0M0S") -> dt:

    utc = pytz.utc

    dt_format = "%Y-%m-%dT%H:%M:%S%z"  # 2020-12-29T13:34:38+00:00
    acc_span = isodate.parse_duration(accuracy)
    start_time = dt.strptime(timestamp, dt_format) - acc_span
    end_time = dt.strptime(timestamp, dt_format) + acc_span

    fake = Faker()
    return fake.date_time_between_dates(start_time, end_time)


def main():
    logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)
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

    logging.info("Processing track name {0}".format(track.name))
    track.segments[0].get_nearest_location(finish_location)

    nearest_location = track.segments[0].points[0]
    shortest_dist = None
    for segment_index, segment in enumerate(track.segments):
        for point_index, point in enumerate(segment.points):
            this_distance = distance.distance(
                (finish_location.latitude, finish_location.longitude),
                (point.latitude, point.longitude),
            )

            logging.debug("Distance from finish: %s", this_distance)

            if shortest_dist is None or this_distance < shortest_dist:
                shortest_dist = this_distance
                nearest_location = point
                gpx_indices = (segment_index, point_index)

    logging.info("Estimated start at %s", start_time)
    logging.info("Finish at %s", finish_time)
    logging.info(
        "Closest GPX track point is (%s,%s)",
        nearest_location.latitude,
        nearest_location.longitude,
    )
    logging.info(
        "%.2f metres away from the finish location and elevation Δ is +%.2f " "metres",
        shortest_dist.m,
        nearest_location.elevation - finish_location.elevation,
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

    track.split(track_segment_no=gpx_indices[0], track_point_no=gpx_indices[1])
    gpx_track.segments.append(track.segments[0])
    gpx_output.fill_time_data_with_regular_intervals(
        start_time=start_time, end_time=finish_time
    )
    print("GPX:", gpx_output.to_xml())

    with open("/home/ieuan/repos/gpx-track-render-er/data/output.gpx", "w") as f:
        f.write(gpx_output.to_xml())


if __name__ == "__main__":
    # execute only if run as a script
    main()
