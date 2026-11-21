#!/usr/bin/env python3
"""Download the TeamLinkt iCal feed and write schedule.json (games only, Pacific time).

Usage: sync_schedule.py <ics-url-or-file> <output.json>
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")


def load(src):
    if re.match(r"^(https?|webcal)://", src):
        src = re.sub(r"^webcal://", "https://", src)
        with urllib.request.urlopen(src, timeout=30) as r:
            return r.read().decode("utf-8")
    return open(src, encoding="utf-8").read()


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def unescape(v):
    return re.sub(r"\\(.)", lambda m: "\n" if m.group(1) in "nN" else m.group(1), v)


def parse_events(text):
    events, cur = [], None
    for line in unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            key, val = line.split(":", 1)
            cur[key.split(";")[0]] = unescape(val)
    return events


def to_pacific(stamp):
    if stamp.endswith("Z"):
        return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(PACIFIC)
    return datetime.strptime(stamp, "%Y%m%dT%H%M%S").replace(tzinfo=PACIFIC)


def to_game(ev):
    desc = ev.get("DESCRIPTION", "")
    if "Event Type: Game" not in desc or ev.get("STATUS") == "CANCELLED":
        return None
    start = to_pacific(ev["DTSTART"])
    summary = ev.get("SUMMARY", "")
    parts = re.split(r"\s+vs\.?\s+", summary, flags=re.I)
    opponent = ""
    if len(parts) == 2:
        a, b = parts
        opponent = b if "panthers" in a.lower() else a
    m = re.search(r"Home/Away:\s*(\w+)", desc)
    return {
        "date": start.strftime("%Y-%m-%d"),
        "time": start.strftime("%-I:%M %p"),
        "opponent": opponent.strip().title(),
        "homeAway": m.group(1) if m else "",
        "location": ev.get("LOCATION", ""),
    }


def main():
    src, out = sys.argv[1], sys.argv[2]
    games = [g for g in map(to_game, parse_events(load(src))) if g]
    games.sort(key=lambda g: (g["date"], g["time"]))
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"games": games}, f, indent=2)
        f.write("\n")
    print(f"wrote {len(games)} game(s) to {out}")


if __name__ == "__main__":
    main()
