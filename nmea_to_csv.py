"""Convert NMEA text file to CSV"""

import re
import sys
from argparse import ArgumentParser, ArgumentTypeError
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue
from time import sleep

FILEOUT_HEADER = "DATE,TIME,LONGITUDE,LATITUDE,HEIGHT"

def main():
    # Retrieve CLI arguments.
    helpdesc: str = (
        f"Converts NMEA data from a specified text file to a CSV file "
        f"containing fields '{FILEOUT_HEADER}'.\n"
        f"NMEA data file must contain as a minimum either GGA or RMC sentences."
    )
    parser = ArgumentParser(
        description=helpdesc,
    )
    parser.add_argument(
        "-i", "--infile",
        help=(
            "Full path and filename of the NMEA file to be converted. "
            "The output file will have identical path and filename, "
            "except with extension '.csv'."
        ),
        type=Path,
        required=True,
    )
    parser.add_argument(
        "-s", "--startdate",
        help=(
            "UTC date at the start of the NMEA file. To be used if there are "
            "no ZDA sentences present in the NMEA data."
            "record in the file. Format: 'yyyy-mm-dd', "
            "Default: None"
        ),
        default=None,
        type=datestamp_type,
    )

    args = parser.parse_args()
    datestamp = None
    timestamp_prev = None
    if args.startdate:
        datestamp = args.startdate
    in_file = args.infile

    out_file = in_file.with_suffix(".csv")
    with open(out_file, "w", encoding="utf-8") as csv_file:
        csv_file.write(f"{FILEOUT_HEADER}\n")

        with open(in_file, encoding="utf-8") as nmea_file:
            zda_exist = False
            nmea_dict = dict()
            for sentence in nmea_file:
                sentence = re.sub(r"^.*\$", "$", sentence.strip())
                nmea_items = sentence.split(sep=",")
                msg_type = nmea_items[0][-3:]

                if msg_type == "ZDA":
                    zda_exist = True
                    datestamp = datetime(
                        int(nmea_items[4]),
                        int(nmea_items[3]),
                        int(nmea_items[2]),
                    )

                if re.match(r"\d{6}\.\d{0,4}", nmea_items[1]):
                    if nmea_items[1][:6] == "240000":
                        # At UTC midnight NMEA timestamp may incorrectly show hrs as 24.
                        nmea_items[1] = "000000.000"
                    timestamp_curr = datetime.strptime(nmea_items[1], "%H%M%S.%f")
                    secs = (
                        timestamp_curr.hour * 3600
                        + timestamp_curr.minute * 60
                        + timestamp_curr.second
                        + timestamp_curr.microsecond / 1e6
                    )
                    timestamp_delta = timedelta(seconds=secs)
                    if not datestamp:
                        msg = (
                            "The NMEA file does not contain ZDA sentences to "
                            "be able to define the date. "
                            "A valid startdate parameter must be specified."
                        )
                        parser.error(msg)

                    timestamp_curr = datestamp + timestamp_delta

                    if not timestamp_prev:
                        timestamp_prev = timestamp_curr
                    nmea_dict["utcTime"] = timestamp_curr

                if msg_type in ("GGA","RMC"):
                    if msg_type == "GGA":
                        lat = nmea_items[2]
                        lat_hemi = nmea_items[3]
                        lon = nmea_items[4]
                        lon_hemi = nmea_items[5]
                        height = nmea_items[9]
                        ht_unit = nmea_items[10]
                    else:
                        lat = nmea_items[3]
                        lat_hemi = nmea_items[4]
                        lon = nmea_items[5]
                        lon_hemi = nmea_items[6]
                        height = 0.0
                    nmea_dict["lat"] = f"{lat[0:2]}\u00b0{lat[2:11]}'{lat_hemi}"
                    nmea_dict["latDec"] = int(lat[0:2]) + float(lat[2:11]) / 60
                    if lat_hemi.upper() == "S":
                        nmea_dict["latDec"] *= -1
                    nmea_dict["lon"] = f"{lon[0:3]}\u00b0{lon[3:12]}'{lon_hemi}"
                    nmea_dict["lonDec"] = int(lon[0:3]) + float(lon[3:12]) / 60
                    if lon_hemi.upper() == "W":
                        nmea_dict["lonDec"] *= -1
                    if ht_unit.upper() == "M":
                        nmea_dict["height"] = float(height)


                # Changing timestamp indicates next block of NMEA messages.
                if timestamp_curr == timestamp_prev:
                    continue

                # Increment the date at 24 hour rollover if ZDA message not present.
                if not zda_exist and timestamp_curr.hour < timestamp_prev.hour:
                    datestamp = datestamp + timedelta(days=1)
                timestamp_prev = timestamp_curr
                zda_exist = False
                # print(f"{nmea_dict}")
                try:
                    csv_file.write(
                        f"{nmea_dict['utcTime'].strftime('%Y/%m/%d')},"
                        f"{nmea_dict['utcTime'].strftime('%H:%M:%S')},"
                        f"{nmea_dict['lonDec']:.8f},"
                        f"{nmea_dict['latDec']:.8f},"
                        f"{nmea_dict['height']:.2f}"
                        f"\n"
                    )
                except (KeyError):
                    # Incomplete NMEA block
                    continue

                nmea_dict = dict()


def datestamp_type(datestamp: str) -> datetime:
    """Argparse type for user datestamp values given from the command line."""
    try:
        datestamp = re.sub(r"[-: _/tT]", "_", datestamp)
        return datetime.strptime(datestamp, "%Y_%m_%d")
    except ValueError as exc:
        msg = (
            f"Specified datestamp ({datestamp}) is not valid! "
            f"Expected format, 'yyyy-mm-dd'!"
        )
        raise ArgumentTypeError(msg) from exc

if __name__ == "__main__":
    main()
