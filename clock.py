"""
What day and time it is in Bangladesh, wherever the server runs.

The server's own clock may be on another time zone (Render runs on UTC, six
hours behind Dhaka), so between midnight and 6 AM it would still think it was
yesterday. Every "which day is it?" question in the site asks here instead.

Bangladesh has no summer time, so it is always UTC + 6 hours.
"""

import datetime as dt

BANGLADESH = dt.timezone(dt.timedelta(hours=6), "Asia/Dhaka")


def now():
    """The time right now in Bangladesh."""
    return dt.datetime.now(BANGLADESH)


def today():
    """Today's date in Bangladesh."""
    return now().date()
