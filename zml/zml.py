# zml.py
"""Creating a Zoom Meeting List."""

import asyncio
from datetime import datetime, timedelta
import http.client
import json
import logging
from operator import itemgetter
import os.path
import pickle
import pytz
from typing import Any, cast, Dict, List, Optional

from rest_tools.server import from_environment  # type: ignore

import dateutil.parser
from googleapiclient.discovery import build  # type: ignore
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from google.auth.transport.requests import Request  # type: ignore


EventType = Dict[str, Any]
MeetingType = Dict[str, Any]

EXPECTED_CONFIG = {
    "CALENDAR_ID": "wisc.edu_7ngpdt69gv42oehujek6hfvfu0@group.calendar.google.com",
    "LOGGING_FORMAT": "%(asctime)-15s [%(threadName)s] %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
    "LOGGING_LEVEL": "INFO",
    "MAX_DAYS": 90,
    "MAX_PAGE_SIZE": 150,
    "RUN_ONCE_AND_DIE": False,
    "WORK_SLEEP_DURATION_SECONDS": 60,
    "ZOOM_TOKEN": None,
}

# If modifying these scopes, delete the file token.pickle.
GOOGLE_SCOPES = [
    # 'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar',
]

LOG = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# The Zoom Section
# -----------------------------------------------------------------------------


async def get_zoom_user_list(token: str, max_page_size: int) -> List[str]:
    """Query the Zoom API to get a list of users on our Zoom account."""
    conn = http.client.HTTPSConnection("api.zoom.us")
    headers = {
        'authorization': f"Bearer {token}",
        'content-type': "application/json",
    }
    conn.request("GET", f"/v2/users?page_number=1&page_size={max_page_size}&status=active", headers=headers)
    res = conn.getresponse()
    data = res.read()
    res_dict = json.loads(data.decode("utf-8"))
    users = res_dict["users"]
    user_list = []
    for user in users:
        user_list.append(user["email"])
    return user_list


async def get_upcoming_meetings_for_zoom_user(token: str, zoom_user: str, max_page_size: int) -> List[MeetingType]:
    """Query the Zoom API to get the list of upcoming meetings for the provided user."""
    conn = http.client.HTTPSConnection("api.zoom.us")
    headers = {
        'authorization': f"Bearer {token}",
        'content-type': "application/json",
    }
    conn.request("GET", f"/v2/users/{zoom_user}/meetings?page_number=1&page_size={max_page_size}&type=upcoming", headers=headers)
    res = conn.getresponse()
    data = res.read()
    res_dict = json.loads(data.decode("utf-8"))
    meetings = res_dict["meetings"]
    meeting_list = []
    for meeting in meetings:
        meeting["user"] = zoom_user
        meeting_list.append(meeting)
    return meeting_list


async def get_all_upcoming_zoom_meetings(token: str, max_page_size: int) -> List[MeetingType]:
    """Query the Zoom API to get a list of all upcoming meetings for all users."""
    users = await get_zoom_user_list(token, max_page_size)
    meetings = []
    for user in users:
        upcoming_meetings = await get_upcoming_meetings_for_zoom_user(token, user, max_page_size)
        meetings.extend(upcoming_meetings)
    return meetings


def filter_and_sort_zoom_meetings(meetings: List[MeetingType], max_days: int) -> List[MeetingType]:
    """Filter and sort the meetings into something sensible."""
    # --------------------------------------------------------------------------
    # Zoom API Documentation
    # Meeting Types:
    # 1 - Instant meeting.
    # 2 - Scheduled meeting.
    # 3 - Recurring meeting with no fixed time.
    # 8 - Recurring meeting with a fixed time.
    # --------------------------------------------------------------------------
    sync_meetings = []
    # first, filter out any meetings that don't have a start_time
    for meeting in meetings:
        if "start_time" in meeting:
            sync_meetings.append(meeting)
    # next, filter out any meetings more than max_days out
    cutoff_time = datetime.utcnow() + timedelta(days=max_days)
    cutoff = cutoff_time.isoformat()
    sync_meetings = [x for x in sync_meetings if x["start_time"] < cutoff]
    # next, sort the meetings by their start_time
    sync_meetings = sorted(sync_meetings, key=itemgetter("start_time"))
    # return the filtered and sorted meetings to the caller
    return sync_meetings


def print_zoom_meetings_as_json(meetings: List[Dict[str, str]]) -> None:
    """Use the print function to output the meetings as pretty-printed JSON."""
    json_meetings = json.dumps(meetings, indent=4, separators=(', ', ': '))
    print(json_meetings)

# -----------------------------------------------------------------------------
# The Google Section
# -----------------------------------------------------------------------------


def get_google_calendar_service() -> Any:
    """Query the Google Calendar API for a list of upcoming events."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', GOOGLE_SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    # build the service object to query the Calendar API
    service = build('calendar', 'v3', credentials=creds)
    # return the service object to the caller
    return service


async def get_all_google_events(service: Any,
                                calendarId: str,
                                maxResults: int) -> List[EventType]:
    """Query the Google Calendar API for a list of upcoming events."""
    # query the Calendar API
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    three_months_ago = subtract_three_months(now)
    print(f'Getting the upcoming {maxResults} events from {three_months_ago} ...')
    events_result = service.events().list(calendarId=calendarId,
                                          timeMin=three_months_ago,
                                          maxResults=maxResults,
                                          singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    return cast(List[EventType], events)


def print_google_events_as_json(events: List[EventType]) -> None:
    """Use the print function to output the calendar events as pretty-printed JSON."""
    json_meetings = json.dumps(events, indent=4, separators=(', ', ': '))
    print(json_meetings)


def subtract_three_months(start_time: str) -> str:
    """Use the start time and duration (minutes) to compute an end time."""
    d = dateutil.parser.parse(start_time)
    d = d.replace(microsecond=0)
    d = d.replace(tzinfo=pytz.UTC)
    cutoff_time = d + timedelta(days=-90)
    cutoff = cutoff_time.isoformat().replace("+00:00", "Z")  # 'Z' indicates UTC time
    return cutoff

# -----------------------------------------------------------------------------
# The Control Section
# -----------------------------------------------------------------------------


def add_duration(start_time: str, duration: int) -> str:
    """Use the start time and duration (minutes) to compute an end time."""
    d = dateutil.parser.parse(start_time)
    d = d.replace(microsecond=0)
    d = d.replace(tzinfo=pytz.UTC)
    cutoff_time = d + timedelta(minutes=duration)
    cutoff = cutoff_time.isoformat().replace("+00:00", "Z")  # 'Z' indicates UTC time
    return cutoff


def as_calendar_event(meeting: MeetingType) -> EventType:
    """Create the corresponding event for the provided zoom meeting."""
    # Example Zoom Meeting:
    # {
    #     "uuid": "yRyX6GUEDSaYV4STzlN5Tw==",
    #     "id": 99912393789,
    #     "host_id": "HJue2nQWV8NgQH3gPVnEZS",
    #     "topic": "Spring 2020 Collaboration Meeting Plenary Sessions",
    #     "type": 8,
    #     "start_time": "2020-05-12T13:00:00Z",
    #     "duration": 180,
    #     "timezone": "America/Chicago",
    #     "created_at": "2020-04-14T20:02:39Z",
    #     "join_url": "https://wipac-science.zoom.us/j/99912393789?pwd=hunter2",
    #     "user": "collaborationmeetings@icecube.wisc.edu"
    # },
    event = {
        'summary': meeting["topic"],
        'description': meeting["join_url"],
        'start': {
            'dateTime': meeting["start_time"],
            'timeZone': meeting["timezone"],
        },
        'end': {
            'dateTime': add_duration(meeting["start_time"], meeting["duration"]),
            'timeZone': meeting["timezone"],
        },
        'location': meeting["user"],
        'extendedProperties': {
            'private': meeting,
        },
    }
    # return the constructed event to the caller
    return event


def configure_logging() -> None:
    # figure out how we want to configure the logging for the service daemon
    config = from_environment(EXPECTED_CONFIG)
    format = config["LOGGING_FORMAT"]
    level = config["LOGGING_LEVEL"]
    # configure the logging appropriately
    logging.basicConfig(format=format)
    LOG = logging.getLogger(__name__)
    LOG.setLevel(level)


def get_corresponding_event(events: List[EventType], meeting: MeetingType) -> Optional[EventType]:
    """Find the corresponding calendar event (if any) for a zoom meeting."""
    for event in events:
        if ("extendedProperties" in event):
            extendedProperties = event["extendedProperties"]
            if "private" in extendedProperties:
                private = extendedProperties["private"]
                if str_equals(meeting, private):
                    return event
    # no event was found
    return None


def log_configuration() -> None:
    # log the way this component has been configured
    config = from_environment(EXPECTED_CONFIG)
    LOG.info("Zoom Meeting List is configured:")
    for name in config:
        LOG.info(f"{name} = {config[name]}")


def str_equals(d0: Dict[str, Any], d1: Dict[str, Any]) -> bool:
    """Check the stringified values of the dictionaries for equality."""
    for k, v in d0.items():
        if not (k in d1):
            return False
        if str(d0[k]) != str(d1[k]):
            return False
    return True


async def sync_zoom_to_google() -> None:
    """Synchronize upcoming Zoom Events to our Google Calendar."""
    # configure ourselves and figure out what we want to do
    config = from_environment(EXPECTED_CONFIG)
    calendarId = config["CALENDAR_ID"]
    max_days = int(config["MAX_DAYS"])
    max_page_size = int(config["MAX_PAGE_SIZE"])
    token = config["ZOOM_TOKEN"]

    LOG.info(f"Synchronizing {max_days} days worth of Zoom Meetings to Google Calendar")

    # query Zoom and get the current list of all meetings
    meetings = await get_all_upcoming_zoom_meetings(token, max_page_size)
    meetings = filter_and_sort_zoom_meetings(meetings, max_days)
    LOG.info(f"Found {len(meetings)} Zoom Meetings to synchronize")
    # print_zoom_meetings_as_json(meetings)

    # query Google and get the current list of all calendar events
    service = get_google_calendar_service()
    events = await get_all_google_events(service, calendarId, max_page_size * 3)
    LOG.info(f"Found {len(events)} Google Calendar Events to synchronize")

    # for each meeting
    for meeting in meetings:
        # try to find the google calendar event that corresponds
        event = get_corresponding_event(events, meeting)
        # if we didn't find one, create one
        if not event:
            new_event = as_calendar_event(meeting)
            new_event = service.events().insert(
                calendarId=calendarId,
                conferenceDataVersion=0,
                sendUpdates="none",
                body=new_event).execute()
            LOG.info(f"Created new Google Calender Event: {new_event.get('htmlLink')}")
        # otherwise, remove it from the event list
        else:
            events.remove(event)

    # for each event that wasn't matched to an upcoming Zoom meeting
    LOG.info(f"Will delete {len(events)} obsolete Google Calender Events")
    for event in events:
        # delete that event from the calendar
        service.events().delete(
            calendarId=calendarId,
            eventId=event["id"],
            sendUpdates="none").execute()

    LOG.info("Finished synchronization work")


async def work_loop() -> None:
    # configure the work loop
    config = from_environment(EXPECTED_CONFIG)
    run_once_and_die = config["RUN_ONCE_AND_DIE"]
    work_sleep_duration_seconds = int(config["WORK_SLEEP_DURATION_SECONDS"])
    # until forever...
    while True:
        # perform the work of synchronizing Zoom to Google
        LOG.info("Starting work cycle")
        await sync_zoom_to_google()
        # if we only wanted a one-shot run, then bail out of the loop
        if run_once_and_die:
            break
        # otherwise, sleep until it's time to perform work again
        LOG.info(f"Sleeping for {work_sleep_duration_seconds} seconds")
        await asyncio.sleep(work_sleep_duration_seconds)


def main() -> None:
    """Run the function to synchronize upcoming Zoom Events to our Google Calendar."""
    configure_logging()
    log_configuration()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(work_loop())


if __name__ == "__main__":
    main()
