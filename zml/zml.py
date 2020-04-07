# zml.py
"""Creating a Zoom Meeting List."""

import asyncio
import csv
from datetime import datetime, timedelta
import http.client
import json
from operator import itemgetter
import pytz
from typing import Dict, List

from rest_tools.server import from_environment  # type: ignore

import dateutil.parser

EXPECTED_CONFIG = {
    # "ZOOM_ACCOUNT_EMAIL": "zoomservice@wipac.wisc.edu",
    # "ZOOM_ACCOUNT_PASSWORD": None,
    # "ZOOM_APP_CLIENT_ID": None,
    # "ZOOM_APP_CLIENT_SECRET": None,
    "ZOOM_TOKEN": None,
}

MAX_DAYS = 30
MAX_PAGE_SIZE = 50


async def get_user_list(token: str) -> List[str]:
    """Query the Zoom API to get a list of users on our Zoom account."""
    conn = http.client.HTTPSConnection("api.zoom.us")
    headers = {
        'authorization': f"Bearer {token}"
    }
    conn.request("GET", f"/v2/users?page_number=1&page_size={MAX_PAGE_SIZE}&status=active", headers=headers)
    res = conn.getresponse()
    data = res.read()
    res_dict = json.loads(data.decode("utf-8"))
    users = res_dict["users"]
    user_list = []
    for user in users:
        user_list.append(user["email"])
    return user_list


async def get_upcoming_meetings_for_user(token: str, zoom_user: str) -> List[Dict[str, str]]:
    """Query the Zoom API to get the list of upcoming meetings for the provided user."""
    conn = http.client.HTTPSConnection("api.zoom.us")
    headers = {
        'authorization': f"Bearer {token}"
    }
    conn.request("GET", f"/v2/users/{zoom_user}/meetings?page_number=1&page_size={MAX_PAGE_SIZE}&type=upcoming", headers=headers)
    res = conn.getresponse()
    data = res.read()
    res_dict = json.loads(data.decode("utf-8"))
    meetings = res_dict["meetings"]
    meeting_list = []
    for meeting in meetings:
        meeting["user"] = zoom_user
        meeting_list.append(meeting)
    return meeting_list


async def get_all_upcoming_meetings(token: str) -> List[Dict[str, str]]:
    """Query the Zoom API to get a list of all upcoming meetings for all users."""
    users = await get_user_list(token)
    meetings = []
    for user in users:
        upcoming_meetings = await get_upcoming_meetings_for_user(token, user)
        meetings.extend(upcoming_meetings)
    return meetings


def filter_and_sort_meetings(meetings: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Filter and sort the meetings into something sensible."""
    # first, sort them into meetings that have a fixed start date or not
    indefinite_meetings = []
    definite_meetings = []
    for meeting in meetings:
        if "start_time" in meeting:
            definite_meetings.append(meeting)
        else:
            indefinite_meetings.append(meeting)
    # next, sort the indefinite meetings by user and title
    indefinite_meetings = sorted(indefinite_meetings, key=itemgetter("topic"))
    indefinite_meetings = sorted(indefinite_meetings, key=itemgetter("user"))
    # next, filter out any definite meetings more than MAX_DAYS out
    cutoff_time = datetime.utcnow() + timedelta(days=MAX_DAYS)
    cutoff = cutoff_time.isoformat()
    definite_meetings = [x for x in definite_meetings if x["start_time"] < cutoff]
    # next, sort the definite meetings by their start date
    definite_meetings = sorted(definite_meetings, key=itemgetter("start_time"))
    # now put the lists back together, indefinite first
    meeting_list = []
    meeting_list.extend(indefinite_meetings)
    meeting_list.extend(definite_meetings)
    # return the filtered and sorted meetings to the caller
    return meeting_list


def print_meetings_as_json(meetings: List[Dict[str, str]]) -> None:
    """Use the print function to output the meetings as pretty-printed JSON."""
    json_meetings = json.dumps(meetings, indent=4, separators=(', ', ': '))
    print(json_meetings)


def print_meetings_as_csv(meetings: List[Dict[str, str]]) -> None:
    """Use the print function to output the meetings in CSV format."""
    with open('meetings.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for meeting in meetings:
            # when
            rowdata = []
            if "start_time" in meeting:
                date = dateutil.parser.isoparse(meeting["start_time"])
                # meeting_tz = pytz.timezone(meeting["timezone"])
                meeting_tz = pytz.timezone("America/Chicago")
                date = date.astimezone(meeting_tz)
                rowdata.append(date.strftime('%Y-%m-%d %H:%M'))
            else:
                rowdata.append("Standing")
            # who
            rowdata.append(meeting["user"])
            # what
            rowdata.append(meeting["topic"].strip())
            # how
            rowdata.append(meeting["join_url"])
            # export the row
            writer.writerow(rowdata)


async def zml():
    """Print a friendly message."""
    config = from_environment(EXPECTED_CONFIG)
    token = config["ZOOM_TOKEN"]
    meetings = await get_all_upcoming_meetings(token)
    meetings = filter_and_sort_meetings(meetings)
    # print_meetings_as_json(meetings)
    print_meetings_as_csv(meetings)


def main() -> None:
    """Run the Zoom Meeting List script."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(zml())


if __name__ == "__main__":
    main()
