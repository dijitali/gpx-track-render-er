import confuse
import datetime
from faker import Faker
from geopy import distance
import gpxpy
import gpxpy.gpx
import logging
import mailbox
import pytz
import srtm
import isodate
import urllib.parse


def guess_timestamp_with_acc(
    timestamp: datetime, accuracy: datetime.timedelta = "PT0H0M0S"
) -> datetime:
    """Generate a random timestamp with the given accuracy

    :param timestamp: The original timestamp to base the randomised one from
    :param accuracy: A
    :return:
    """

    dt_format = "%Y-%m-%dT%H:%M:%S%z"  # 2020-12-29T13:34:38+00:00

    start_time = datetime.datetime.strptime(timestamp, dt_format) - accuracy
    end_time = datetime.datetime.strptime(timestamp, dt_format) + accuracy

    # TODO: does this really need the whole Faker module?
    #  could probably simplify this or remove the functionality altogether
    fake = Faker()
    return fake.date_time_between_dates(start_time, end_time)


def get_spot_coordinates_from_mbox(mbox_filename: str) -> list:
    message_locations = []
    for message in mailbox.mbox(mbox_filename):
        if {"X-SPOT-Latitude", "X-SPOT-Longitude", "X-SPOT-Time", "X-SPOT-Type"} <= set(
            message.keys()
        ) and message["X-SPOT-Type"] == "Check-in/OK":

            message_locations.append(
                gpxpy.gpx.GPXTrackPoint(
                    latitude=message["X-SPOT-Latitude"],
                    longitude=message["X-SPOT-Longitude"],
                    elevation=None,
                    time=pytz.utc.localize(
                        datetime.datetime.utcfromtimestamp(int(message["X-SPOT-Time"]))
                    ),
                )
            )
            logging.debug("Found message")
        else:

            logging.debug("Ignoring message that does not match filter")

    message_locations.sort(key=lambda m: m.time)
    logging.debug(f"Found a total of {message_locations.__len__()} coordinates in MBOX")
    return message_locations


def get_single_activity(start_location, end_location, gpx_track):
    logging.debug("Importing configuration data")


def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    logging.debug("Importing configuration data")

    config = confuse.Configuration("gpx_track_render_er", __name__)
    config.set_file("config_default.yaml")

    logging.info("Reading Spot GPS coordinates from MBOX")
    spot_checkin_locations = get_spot_coordinates_from_mbox(
        mbox_filename=config["mbox_data"]["filename"].as_filename()
    )

    start_time = guess_timestamp_with_acc(
        config["start"]["time"]["timestamp"].get(str),
        isodate.parse_duration(config["start"]["time"]["accuracy"].get(str)),
    )
    finish_time = guess_timestamp_with_acc(
        config["finish"]["time"]["timestamp"].get(str),
        isodate.parse_duration(config["finish"]["time"]["accuracy"].get(str)),
    )

    logging.info(f"Estimated start at {start_time}")
    logging.info(f"Finish at {finish_time}")

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

    gpx = gpxpy.parse(open(config["gpx_data"]["filename"].as_filename(), "r"))
    track = next(
        (x for x in gpx.tracks if x.name == config["gpx_data"]["track_name"].get(str)),
        None,
    )
    logging.info(f"Processing track name {track.name}")

    nearest_location = track.segments[0].get_nearest_location(finish_location)
    shortest_dist = distance.distance(
        (finish_location.latitude, finish_location.longitude),
        (nearest_location.location.latitude, nearest_location.location.longitude),
    )
    logging.info(
        f"Closest GPX track point is ({nearest_location.location.latitude},{nearest_location.location.longitude})"
    )
    logging.info(
        f"Closest point along route is {shortest_dist.meters:.2f} metres away from the finish location and elevation Δ "
        f"is {(nearest_location.location.elevation - finish_location.elevation):+.2f} metres from the route"
    )

    max_distance_from_gpx = config["max_distance_from_gpx"].get(int)
    if shortest_dist > max_distance_from_gpx:
        logging.warning(
            f"Closest point found along GPX route is over the configured threshold of "
            f"{max_distance_from_gpx} meters away.  It was "
        )
        # TODO: skip this day's data
    else:
        # TODO: add day to processing queue
        logging.debug("Processing day")

    gmaps_params = urllib.parse.urlencode(
        {
            "api": 1,
            "basemap": "terrain",
            "origin": (finish_location.latitude, finish_location.longitude),
            "destination": (
                nearest_location.location.latitude,
                nearest_location.location.longitude,
            ),
        }
    )
    print(f"View at : https://www.google.com/maps/dir/?{gmaps_params}")

    gpx_output = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_output.tracks.append(gpx_track)

    track.split(
        track_segment_no=nearest_location.segment_no,
        track_point_no=nearest_location.point_no,
    )
    gpx_track.segments.append(track.segments[0])
    gpx_output.fill_time_data_with_regular_intervals(
        start_time=start_time, end_time=finish_time
    )
    # TODO: enrich GPX file with additional metadata (investigate what a regular Garmin device contains)
    with open("/home/ieuan/repos/gpx-track-render-er/data/output.gpx", "w") as f:
        f.write(gpx_output.to_xml())


if __name__ == "__main__":
    # execute only if run as a script
    main()
