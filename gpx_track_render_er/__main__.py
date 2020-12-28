import datetime
import gpxpy
import gpxpy.gpx
import urllib.parse
from geopy import distance


def main():
    finish_time = datetime.datetime(2016, 4, 12, 1, 54, 41)
    finish_location = (33.27477, -116.64574)
    shortest_dist = distance.distance(meters=100000)

    gpx_file = open("CA_Sec_A_tracks.gpx", "r")

    gpx = gpxpy.parse(gpx_file)

    for track in gpx.tracks:
        print("Processing track name {0}".format(track.name))
        for segment in track.segments:
            for point in segment.points:
                this_distance = distance.distance(
                    finish_location, (point.latitude, point.longitude)
                )

                print("Distance from finish: {0}".format(this_distance))

                if this_distance < shortest_dist:
                    shortest_dist = this_distance
                    nearest_location = point

    print(
        "Closest point is ({0},{1}) -> {2} metres away ".format(
            nearest_location.latitude,
            nearest_location.longitude,
            round(shortest_dist.m, 2),
        )
    )
    gmaps_params = urllib.parse.urlencode(
        {
            "api": 1,
            "basemap": "terrain",
            "origin": finish_location,
            "destination": (nearest_location.latitude, nearest_location.longitude),
        }
    )
    print("View at : https://www.google.com/maps/dir/?{0}".format(gmaps_params))


if __name__ == "__main__":
    # execute only if run as a script
    main()
