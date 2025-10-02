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
) -> dict:
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", output)
    sections = re.split(r"\n\s*\n", clean_output.strip())
    data = {}

    for sec in sections:
        lines = sec.strip().splitlines()
        if not lines:
            continue

        name = lines[0].strip()
        if not name.startswith("Current "):
            continue

        usage_match = re.search(r"(\d+)% used", sec)
        usage = int(usage_match.group(1)) if usage_match else None

        reset_match = re.search(r"Resets (.+)", sec)
        reset_raw = reset_match.group(1).strip() if reset_match else None

        reset_iso = None
        resets_second: int | None = None
        if reset_raw:
            try:
                tz_match = re.search(r"\((.+)\)", reset_raw)
                tz_name = tz_match.group(1) if tz_match else "UTC"
                dt_str = re.sub(r"\(.+\)", "", reset_raw).strip()

                tz = pytz.timezone(tz_name)
                dt = parser.parse(dt_str)
                reset_iso = tz.localize(dt).isoformat()
                resets_second = int((dt - now).total_seconds())
            except Exception:
                pass

        data[
            name.lower()
            .replace("(", "")
            .replace(")", "")
            .replace(" ", "_")
            .replace("current_", "")
        ] = {
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
):
    output: str = get_output(
        wait=wait,
        cmd=f"{path_bin} /usage",
    )

    now: datetime = datetime.now()
    data: dict = parse(
        output=output,
        now=now,
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
    return oparser.parse_args()


def main() -> None:
    opts = get_opts()
    operation(
        wait=opts.wait,
        path_out=opts.output,
        path_bin=opts.bin,
    )


if __name__ == "__main__":
    main()
