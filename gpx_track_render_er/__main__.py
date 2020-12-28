import datetime
import gpxpy
import gpxpy.gpx
from geopy import distance


def main():
    finish_time = datetime.datetime(2016, 4, 12, 1, 54, 41)
    finish_location = (32.62244, -116.51799)
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

                print(
                    "Point at ({0},{1}) -> {2}".format(
                        point.latitude, point.longitude, point.elevation
                    )
                )
                print("Distance from finish: {0}".format(this_distance))

                if this_distance < shortest_dist:
                    shortest_dist = this_distance
                    nearest_location = point

    print(
        "Closest point is ({0},{1}) -> {2} ".format(
            nearest_location.latitude,
            nearest_location.longitude,
            nearest_location.elevation,
        )
    )


if __name__ == "__main__":
    # execute only if run as a script
    main()
