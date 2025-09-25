#!/usr/bin/env python3
import json
import argparse
from datetime import datetime, date, time, timedelta, UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import uuid

WEEKDAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def parse_time(s: str) -> time:
    return datetime.strptime(s, "%H:%M").time()


def expand_day_pattern(pattern: str) -> list:
    pattern = pattern.strip()
    if pattern.lower() == "daily":
        return WEEKDAYS[:]
    if "-" in pattern and "," not in pattern:
        a,b = pattern.split("-")
        ai, bi = WEEKDAYS.index(a), WEEKDAYS.index(b)
        return WEEKDAYS[ai:bi+1]
    parts = [p.strip() for p in pattern.split(",")]
    for p in parts:
        if p not in WEEKDAYS:
            raise ValueError(f"Invalid day in pattern: {p}")
    return parts


def to_utc_strings(local_date: date, local_time: time, tz: ZoneInfo, duration_minutes: int = 60):
    start_local = datetime.combine(local_date, local_time).replace(tzinfo=tz)
    end_local = start_local + timedelta(minutes=duration_minutes)
    start_utc = start_local.astimezone(ZoneInfo("UTC"))
    end_utc = end_local.astimezone(ZoneInfo("UTC"))
    return start_utc.strftime("%Y%m%dT%H%M%SZ"), end_utc.strftime("%Y%m%dT%H%M%SZ")


def fold_ics_text(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s.replace("\n", "\\n")


def linear_progression_value(start, target, weeks, week_index):
    if weeks <= 1:
        return target
    delta = (target - start) / (weeks - 1)
    val = start + delta * week_index
    if isinstance(start, int) and isinstance(target, int):
        return int(round(val))
    return round(val, 2)


def build_progression_text(ev, wk):
    if "progression" in ev and ev["progression"]:
        idx = min(wk, len(ev["progression"]) - 1)
        return f"Week {wk+1}: {ev['progression'][idx]}"
    lp = ev.get("linear_progression")
    if lp:
        start = lp["start"]
        target = lp["target"]
        weeks = lp.get("weeks")
        fmt = lp.get("format", "{value}")
        if not weeks:
            raise ValueError("linear_progression requires 'weeks'")
        val = linear_progression_value(start, target, weeks, wk if wk < weeks else weeks-1)
        return f"Week {wk+1}: " + fmt.format(value=val, week=wk+1)
    return f"Week {wk+1}: {ev.get('description','')}".strip()


def build_meal_text(ev):
    groups = []
    opts = ev.get("options")
    if isinstance(opts, dict):
        for k in ["breakfast","lunch","dinner","snacks"]:
            if k in opts and opts[k]:
                items = "\\n- " + "\\n- ".join(opts[k])
                groups.append(f"{k.title()} options:{items}")
    elif isinstance(opts, list):
        groups.append("Options:\\n- " + "\\n- ".join(opts))
    else:
        groups.append("Options: (none provided)")
    return "\\n\\n".join(groups)


def build_supp_text(ev):
    details = ev.get("details", [])
    if not details:
        return "Take: (no items provided)"
    return "Take:\\n- " + "\\n- ".join(details)


def add_event(lines, start_utc, end_utc, summary, descr, loc=None):
    uid = f"{uuid.uuid4()}@ptplan"
    lines.append("BEGIN:VEVENT")
    lines.append(f"DTSTART:{start_utc}")
    lines.append(f"DTEND:{end_utc}")
    lines.append(f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}")
    lines.append(f"UID:{uid}")
    lines.append(f"SUMMARY:{fold_ics_text(summary)}")
    if loc:
        lines.append(f"LOCATION:{fold_ics_text(loc)}")
    if descr:
        lines.append(f"DESCRIPTION:{fold_ics_text(descr)}")
    lines.append("END:VEVENT")


def create_ics_from_json(cfg: dict, out_path: str):
    try:
        tz = ZoneInfo(cfg["timezone"])
    except (KeyError, ZoneInfoNotFoundError):
        tz = ZoneInfo("UTC")

    start_date = datetime.strptime(cfg["start_date"], "%Y-%m-%d").date()
    weeks = int(cfg.get("weeks", 4))
    default_duration = int(cfg.get("default_duration_minutes", 60))

    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//PT Plan//EN")
    lines.append(f"X-WR-CALNAME:{cfg.get('calendar_name','PT_Plan')}")
    lines.append(f"X-WR-TIMEZONE:{cfg.get('timezone','UTC')}")

    WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for ev in cfg.get("events", []):
        name = ev["name"]
        etype = ev.get("type","note")
        time_str = ev.get("time","07:00")
        duration = int(ev.get("duration_minutes", default_duration))
        pattern = ev.get("day_of_week","Daily")
        if isinstance(pattern, list):
            days = pattern
        else:
            days = expand_day_pattern(pattern)

        for wk in range(weeks):
            for day in days:
                day_idx = WEEKDAYS.index(day)
                event_date = start_date + timedelta(days = wk*7 + day_idx)
                start_utc, end_utc = to_utc_strings(event_date, datetime.strptime(time_str, "%H:%M").time(), tz, duration)

                if etype == "workout":
                    descr = build_progression_text(ev, wk)
                elif etype == "meal":
                    descr = build_meal_text(ev)
                elif etype == "supplement":
                    descr = build_supp_text(ev)
                else:
                    descr = ev.get("description","")

                add_event(lines, start_utc, end_utc, name, descr, loc=ev.get("location"))

    lines.append("END:VCALENDAR")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate ICS from JSON plan")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--out", default="plan.ics", help="Output ICS path")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    out_path = create_ics_from_json(cfg, args.out)
    print(f"ICS written to: {out_path}")


if __name__ == "__main__":
    main()
