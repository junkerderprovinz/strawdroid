#!/usr/bin/env python3
"""Drives the emulator's GPS along a GPX track, one fix per second, so apps see
a moving device with altitude and speed instead of a jump from point to point."""
import argparse
import math
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime

EARTH_M = 6371008.8
KNOTS_PER_MS = 1.943844


def points(path):
    root = ET.parse(path).getroot()
    out = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("trkpt", "rtept"):
            continue
        ele = when = None
        for child in el:
            name = child.tag.rsplit("}", 1)[-1]
            if name == "ele" and child.text:
                ele = float(child.text)
            elif name == "time" and child.text:
                when = datetime.fromisoformat(child.text.strip().replace("Z", "+00:00")).timestamp()
        out.append((float(el.attrib["lat"]), float(el.attrib["lon"]), ele, when))
    return out


def distance(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * EARTH_M * math.asin(math.sqrt(h))


def legs(track, kmh, speedup):
    """Seconds each leg takes: from the GPX times, or from a fixed speed when the
    track has none or one is asked for."""
    timed = kmh is None and all(p[3] is not None for p in track)
    speed = (kmh if kmh is not None else 5.0) / 3.6
    for a, b in zip(track, track[1:]):
        metres = distance(a, b)
        seconds = (b[3] - a[3]) if timed else metres / speed
        yield a, b, metres, max(seconds / speedup, 0.001), max(seconds, 0.001)


def fix(lat, lon, ele, knots):
    # The console takes longitude first; altitude, satellites and speed in knots follow.
    args = ["adb", "emu", "geo", "fix", f"{lon:.7f}", f"{lat:.7f}", f"{ele or 0:.1f}", "8", f"{knots:.2f}"]
    subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def main():
    p = argparse.ArgumentParser(prog="sk route")
    p.add_argument("gpx")
    p.add_argument("--kmh", type=float, help="constant speed, ignoring the times in the file")
    p.add_argument("--speedup", type=float, default=1.0, help="play the track this many times faster")
    p.add_argument("--loop", action="store_true")
    a = p.parse_args()

    track = points(a.gpx)
    if len(track) < 2:
        sys.exit(f"{a.gpx} has fewer than two track points")
    total = sum(distance(x, y) for x, y in zip(track, track[1:]))
    print(f"{len(track)} points, {total / 1000:.2f} km. Ctrl-C stops.", flush=True)

    while True:
        for start, end, metres, wall, real in legs(track, a.kmh, a.speedup):
            knots = metres / real * KNOTS_PER_MS
            steps = max(1, round(wall))
            for i in range(steps):
                f = i / steps
                ele = None
                if start[2] is not None and end[2] is not None:
                    ele = start[2] + (end[2] - start[2]) * f
                fix(start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f, ele, knots)
                time.sleep(wall / steps)
        fix(track[-1][0], track[-1][1], track[-1][2], 0)
        if not a.loop:
            break
    print("Arrived.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
