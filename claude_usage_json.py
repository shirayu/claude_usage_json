#!/usr/bin/env python3

import argparse
import json
import re
import time

import pexpect
import pytz
from dateutil import parser


def get_output(
    *,
    wait: int,
    cmd: str = "claude /usage",
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


def parse(*, output: str) -> dict:
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
        if reset_raw:
            try:
                tz_match = re.search(r"\((.+)\)", reset_raw)
                tz_name = tz_match.group(1) if tz_match else "UTC"
                dt_str = re.sub(r"\(.+\)", "", reset_raw).strip()

                tz = pytz.timezone(tz_name)
                dt = parser.parse(dt_str)
                dt = tz.localize(dt)

                reset_iso = dt.isoformat()
            except Exception:
                reset_iso = None

        data[name] = {"usage_percent": usage, "resets": reset_iso}

    return data


def operation(
    *,
    wait: int,
):
    output: str = get_output(wait=wait)
    data: dict = parse(output=output)
    json_data = json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )
    print(json_data)


def get_opts() -> argparse.Namespace:
    oparser = argparse.ArgumentParser()
    oparser.add_argument(
        "--wait",
        type=int,
        default=3,
        required=False,
    )
    return oparser.parse_args()


def main() -> None:
    opts = get_opts()
    operation(
        wait=opts.wait,
    )


if __name__ == "__main__":
    main()
