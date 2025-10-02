#!/usr/bin/env python3

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from claude_usage_json import parse, recalc_time


class TestParse(unittest.TestCase):
    def test_reset_time_next_day(self):
        """Test that reset time at 3am is interpreted as next day when current time is after 3am"""
        # Current time: 2025-10-02 22:11:04 (JST)
        now = datetime(2025, 10, 2, 22, 11, 4)

        # Mock output with reset time at 3am
        output = """
Current Session

1% used
Resets 3am (Asia/Tokyo)


Current Week (All Models)

5% used
Resets Thu, Oct 9, 7am (Asia/Tokyo)
"""

        result = parse(output=output, now=now)

        # Reset time should be 2025-10-03 03:00:00 (next day), not 2025-10-02 03:00:00 (past)
        self.assertEqual(result["session"]["resets"], "2025-10-03T03:00:00+09:00")

        # resets_second should be positive (time until reset)
        self.assertGreater(result["session"]["resets_second"], 0)

        # Should be approximately 4h 49m (17340 seconds)
        self.assertAlmostEqual(result["session"]["resets_second"], 17340, delta=60)

    def test_reset_time_same_day(self):
        """Test that reset time at 3am is interpreted as same day when current time is before 3am"""
        # Current time: 2025-10-02 01:30:00 (JST)
        now = datetime(2025, 10, 2, 1, 30, 0)

        output = """
Current Session

1% used
Resets 3am (Asia/Tokyo)
"""

        result = parse(output=output, now=now)

        # Reset time should be 2025-10-02 03:00:00 (same day)
        self.assertEqual(result["session"]["resets"], "2025-10-02T03:00:00+09:00")

        # resets_second should be positive (1h 30m = 5400 seconds)
        self.assertAlmostEqual(result["session"]["resets_second"], 5400, delta=60)

    def test_full_datetime_format(self):
        """Test parsing of full datetime format like 'Thu, Oct 9, 7am'"""
        now = datetime(2025, 10, 2, 22, 11, 4)

        output = """
Current Week (All Models)

5% used
Resets Thu, Oct 9, 7am (Asia/Tokyo)
"""

        result = parse(output=output, now=now)

        # Should parse correctly as Oct 9, 2025, 7am
        self.assertEqual(
            result["week_all_models"]["resets"], "2025-10-09T07:00:00+09:00"
        )
        self.assertGreater(result["week_all_models"]["resets_second"], 0)

    def test_lowercase_current(self):
        """Test parsing with lowercase 'current' in section names"""
        now = datetime(2025, 10, 2, 22, 11, 4)

        output = """
Current session

10% used
Resets 3am (Asia/Tokyo)


Current week (all models)

6% used
Resets Oct 9, 7am (Asia/Tokyo)


Current week (Opus)

0% used
"""

        result = parse(output=output, now=now)

        # Should parse all three sections
        self.assertEqual(result["session"]["usage_percent"], 10)
        self.assertEqual(result["session"]["resets"], "2025-10-03T03:00:00+09:00")
        self.assertGreater(result["session"]["resets_second"], 0)

        self.assertEqual(result["week_all_models"]["usage_percent"], 6)
        self.assertEqual(result["week_all_models"]["resets"], "2025-10-09T07:00:00+09:00")
        self.assertGreater(result["week_all_models"]["resets_second"], 0)

        self.assertEqual(result["week_opus"]["usage_percent"], 0)
        self.assertIsNone(result["week_opus"]["resets"])
        self.assertIsNone(result["week_opus"]["resets_second"])

    def test_no_reset_time(self):
        """Test parsing when no reset time is present"""
        now = datetime(2025, 10, 2, 22, 11, 4)

        output = """
Current week (Opus)

0% used
"""

        result = parse(output=output, now=now)

        self.assertEqual(result["week_opus"]["usage_percent"], 0)
        self.assertIsNone(result["week_opus"]["resets"])
        self.assertIsNone(result["week_opus"]["resets_second"])

    def test_with_ansi_codes(self):
        """Test parsing output with ANSI escape codes"""
        now = datetime(2025, 10, 2, 22, 11, 4)

        output = """
\x1b[1mCurrent session\x1b[22m
\x1b[48;2;80;83;112m████▌\x1b[49m 10% used
\x1b[2mResets 3am (Asia/Tokyo)\x1b[22m
"""

        result = parse(output=output, now=now)

        self.assertEqual(result["session"]["usage_percent"], 10)
        self.assertEqual(result["session"]["resets"], "2025-10-03T03:00:00+09:00")
        self.assertGreater(result["session"]["resets_second"], 0)


class TestRecalcTime(unittest.TestCase):
    def test_recalc_time_updates_time_and_resets_second(self):
        """Test that recalc_time updates time and resets_second fields"""
        # Create a temporary input file with fixed time
        test_data = {
            "session": {
                "resets": "2025-10-03T03:00:00+09:00",
                "resets_second": 15971,
                "usage_percent": 11,
            },
            "time": "2025-10-02T22:33:48.831581",
            "week_all_models": {
                "resets": "2025-10-09T07:00:00+09:00",
                "resets_second": 548771,
                "usage_percent": 6,
            },
            "week_opus": {
                "resets": None,
                "resets_second": None,
                "usage_percent": 0,
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_in:
            json.dump(test_data, tmp_in)
            tmp_in_path = Path(tmp_in.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_out:
            tmp_out_path = Path(tmp_out.name)

        try:
            # Run recalc_time
            recalc_time(path_in=tmp_in_path, path_out=tmp_out_path)

            # Read the result
            with tmp_out_path.open("r") as f:
                result = json.load(f)

            # Verify that time was updated (should be different from original)
            self.assertNotEqual(result["time"], test_data["time"])

            # Verify that time is in ISO format and recent
            result_time = datetime.fromisoformat(result["time"])
            now = datetime.now()
            time_diff = abs((now - result_time).total_seconds())
            self.assertLess(time_diff, 5)  # Should be within 5 seconds

            # Verify that resets_second was recalculated (should be different)
            self.assertNotEqual(
                result["session"]["resets_second"], test_data["session"]["resets_second"]
            )
            self.assertNotEqual(
                result["week_all_models"]["resets_second"],
                test_data["week_all_models"]["resets_second"],
            )

            # Verify that other fields remain unchanged
            self.assertEqual(
                result["session"]["resets"], test_data["session"]["resets"]
            )
            self.assertEqual(
                result["session"]["usage_percent"], test_data["session"]["usage_percent"]
            )
            self.assertEqual(
                result["week_all_models"]["resets"],
                test_data["week_all_models"]["resets"],
            )
            self.assertEqual(
                result["week_all_models"]["usage_percent"],
                test_data["week_all_models"]["usage_percent"],
            )
            self.assertEqual(
                result["week_opus"]["resets"], test_data["week_opus"]["resets"]
            )
            self.assertEqual(
                result["week_opus"]["resets_second"],
                test_data["week_opus"]["resets_second"],
            )

        finally:
            tmp_in_path.unlink()
            tmp_out_path.unlink()

    def test_recalc_time_handles_null_resets(self):
        """Test that recalc_time handles null resets correctly"""
        test_data = {
            "time": "2025-10-02T22:33:48.831581",
            "week_opus": {
                "resets": None,
                "resets_second": None,
                "usage_percent": 0,
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_in:
            json.dump(test_data, tmp_in)
            tmp_in_path = Path(tmp_in.name)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_out:
            tmp_out_path = Path(tmp_out.name)

        try:
            recalc_time(path_in=tmp_in_path, path_out=tmp_out_path)

            with tmp_out_path.open("r") as f:
                result = json.load(f)

            # Verify that null values remain null
            self.assertIsNone(result["week_opus"]["resets"])
            self.assertIsNone(result["week_opus"]["resets_second"])

        finally:
            tmp_in_path.unlink()
            tmp_out_path.unlink()


if __name__ == "__main__":
    unittest.main()
