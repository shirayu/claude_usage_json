#!/usr/bin/env python3

import unittest
from datetime import datetime

from claude_usage_json import parse


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


if __name__ == "__main__":
    unittest.main()
