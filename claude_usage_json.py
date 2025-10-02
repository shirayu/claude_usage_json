#!/usr/bin/env python3

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pexpect
import pytz
from dateutil import parser


def get_output(
    *,
    wait: int,
    cmd: str,
    timeout: int = 1,
) -> str:
    child = pexpect.spawn(cmd)

    time.sleep(wait)

    try:
        output_bytes = child.read_nonblocking(
            size=10000,
            timeout=timeout,
        )
    except pexpect.exceptions.EOF:
        output_bytes = b""

    output = output_bytes.decode("utf-8", errors="ignore")

    child.terminate(force=True)

    return output


def parse(
    *,
    output: str,
    now: datetime,
    debug: bool = False,
) -> dict:
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", output)
    sections = re.split(r"\n\s*\n", clean_output.strip())
    data = {}

    i = 0
    while i < len(sections):
        sec = sections[i]
        if debug:
            sys.stderr.write(f"\n=== Section {i} ===\n{repr(sec)}\n")
        lines = sec.strip().splitlines()
        if not lines:
            i += 1
            continue

        name = lines[0].strip()

        # Check if this is a title line (case-insensitive)
        if not name.lower().startswith("current "):
            i += 1
            continue

        # Check if usage/resets are in the same section or next section
        usage_match = re.search(r"(\d+)% used", sec)
        reset_match = re.search(r"Resets (.+)", sec, re.IGNORECASE)

        # If not found in current section, check next section
        if not usage_match and i + 1 < len(sections):
            next_sec = sections[i + 1]
            usage_match = re.search(r"(\d+)% used", next_sec)
            reset_match = re.search(r"Resets (.+)", next_sec, re.IGNORECASE)
            i += 1  # Skip next section as we've already processed it

        usage = int(usage_match.group(1)) if usage_match else None
        reset_raw = reset_match.group(1).strip() if reset_match else None
        i += 1

        reset_iso = None
        resets_second: int | None = None
        if reset_raw:
            try:
                from datetime import timedelta

                tz_match = re.search(r"\((.+)\)", reset_raw)
                tz_name = tz_match.group(1) if tz_match else "UTC"
                dt_str = re.sub(r"\(.+\)", "", reset_raw).strip()

                tz = pytz.timezone(tz_name)
                # Use default date/time, but parse will override the parts present in dt_str
                default_dt = now.replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=None
                )
                dt = parser.parse(dt_str, default=default_dt)
                dt_localized = tz.localize(dt)

                # If the reset time is in the past, assume it's for the next day
                if dt_localized < tz.localize(now):
                    dt = dt + timedelta(days=1)
                    dt_localized = tz.localize(dt)

                reset_iso = dt_localized.isoformat()
                now_localized = (
                    tz.localize(now) if now.tzinfo is None else now.astimezone(tz)
                )
                resets_second = int((dt_localized - now_localized).total_seconds())
            except Exception:
                pass

        key = (
            name.lower()
            .replace("(", "")
            .replace(")", "")
            .replace(" ", "_")
            .replace("current_", "")
        )
        data[key] = {
            "usage_percent": usage,
            "resets": reset_iso,
            "resets_second": resets_second,
        }

    return data


def operation(
    *,
    wait: int,
    path_out: Path,
    path_bin: str,
    debug: bool = False,
):
    output: str = get_output(
        wait=wait,
        cmd=f"{path_bin} /usage",
    )

    if debug:
        sys.stderr.write("=== Raw output ===\n")
        sys.stderr.write(output)
        sys.stderr.write("\n=== End raw output ===\n")

    now: datetime = datetime.now()
    data: dict = parse(
        output=output,
        now=now,
        debug=debug,
    )
    if len(data) == 0:
        sys.stderr.write("Failed to get usage data.\n")
        sys.exit(1)

    data["time"] = now.isoformat()
    json_data = json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )

    if str(path_out) == "/dev/stdout":
        sys.stdout.write(json_data)
        sys.stdout.write("\n")
    else:
        with path_out.open("w") as outf:
            outf.write(json_data)
            outf.write("\n")


def get_opts() -> argparse.Namespace:
    oparser = argparse.ArgumentParser()
    oparser.add_argument(
        "--wait",
        type=int,
        default=3,
        required=False,
    )
    oparser.add_argument(
        "--bin",
        type=str,
        default="claude",
        required=False,
    )
    oparser.add_argument(
        "--output",
        "-o",
        type=Path,
        default="/dev/stdout",
        required=False,
    )
    oparser.add_argument(
        "--debug",
        action="store_true",
        help="Print raw output before parsing",
    )
    oparser.add_argument(
        "--only-calc-time",
        type=Path,
        help="Only recalculate time and resets_second from existing JSON file",
    )
    return oparser.parse_args()


def recalc_time(*, path_in: Path, path_out: Path):
    with path_in.open("r") as inf:
        data = json.load(inf)

    now = datetime.now()

    # Update time
    data["time"] = now.isoformat()

    # Recalculate resets_second for each section
    for key, value in data.items():
        if key == "time":
            continue
        if isinstance(value, dict) and "resets" in value:
            reset_iso = value["resets"]
            if reset_iso:
                try:
                    reset_dt = parser.isoparse(reset_iso)
                    now_with_tz = (
                        now.astimezone(reset_dt.tzinfo) if now.tzinfo is None else now
                    )
                    resets_second = int((reset_dt - now_with_tz).total_seconds())
                    if resets_second < 0:
                        resets_second = 0
                    value["resets_second"] = resets_second
                except Exception:
                    pass

    json_data = json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )

    if str(path_out) == "/dev/stdout":
        sys.stdout.write(json_data)
        sys.stdout.write("\n")
    else:
        with path_out.open("w") as outf:
            outf.write(json_data)
            outf.write("\n")


def main() -> None:
    opts = get_opts()

    if opts.only_calc_time:
        recalc_time(
            path_in=opts.only_calc_time,
            path_out=opts.output,
        )
    else:
        operation(
            wait=opts.wait,
            path_out=opts.output,
            path_bin=opts.bin,
            debug=opts.debug,
        )


if __name__ == "__main__":
    main()
