"""To use this script, install the provided requirements.txt file and
supply a secrets.py file with the required parameters listed below.

JSON records will be written into the specified file and HTML reports
will be written into an outputs filter under the provided directory.
"""


from datetime import datetime, timedelta
from jinja2 import Template
from ua_parser import user_agent_parser

import collections
import json
import os
import requests
import secrets
import smtplib

# This is the absolute path to the directory where you'd like
# the JSON and HTML files to be written.
# The template HTML file should also be placed in this
# directory.
DIR = (
    secrets.DIR
    if hasattr(secrets, "DIR")
    else os.path.dirname(os.path.abspath(__file__))
)
# This is the name of the JSON file that you'd like to write to
FILENAME = secrets.FILENAME
# This is the username for your LA1 login
USERNAME = secrets.USERNAME
# This is the password for your LA1 login
PASSWORD = secrets.PASSWORD
# Email address from which you'd like to send viewer information
FROM_EMAIL = secrets.FROM_EMAIL if hasattr(secrets, "FROM_EMAIL") else None
# Readable name for who is sending the report (e.g. Production Team)
FROM_NAME = secrets.FROM_NAME
# Email address to which you'd like to send viewer information
TO_EMAIL = secrets.TO_EMAIL if hasattr(secrets, "TO_EMAIL") else None
# Prefix to the subject in email reports
EMAIL_SUBJECT_PREFIX = secrets.EMAIL_SUBJECT_PREFIX
# SMTP credentials for sending emails
SMTP_USERNAME = secrets.SMTP_USERNAME if hasattr(secrets, "SMTP_USERNAME") else None
SMTP_PASSWORD = secrets.SMTP_PASSWORD if hasattr(secrets, "SMTP_PASSWORD") else None

API_HOSTNAME = "central.resi.io"

if not USERNAME or not PASSWORD:
    raise Exception("Username and password to LA1 required.")
print(
    f"""Directory in use: {DIR}
Filename in use: {FILENAME}
"""
)

if not FROM_EMAIL or not TO_EMAIL:
    print("Skipping email since from or to emails are not provided.")
else:
    print("Email Template")
    print(
        f"""From: {FROM_NAME} <{FROM_EMAIL}>
To: {TO_EMAIL}
Subject: {EMAIL_SUBJECT_PREFIX} [EVENT NAME WILL GO HERE]
"""
    )




def format_minutes(minutes):
    """Format minutes as hours and minutes, e.g. '22h 27m' or '45m'"""
    total_mins = int(minutes)
    hours = total_mins // 60
    mins = total_mins % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    else:
        return f"{mins}m"


def send_email(event):
    # This server is Gmail's Restricted SMTP Server and will only work for
    # sending emails to G Suite or Gmail accounts.
    # See https://support.google.com/a/answer/176600?hl=en

    # Build city breakdown list
    city_breakdown = ""
    if "city_data" in event and event["city_data"]:
        city_breakdown = "Viewer breakdown by city:\n"
        for location in event["city_data"]:
            city = location["city"]
            region = location["region"]
            viewers = location["none"]["viewers"]
            city_breakdown += f"{city}, {region}: {viewers}\n"

    avg_watch_time = format_minutes(event['public_info'].get('averageViewMinutes', 0))
    median_watch_time = format_minutes(event['public_info'].get('medianWatchTime', 0) / 60)
    total_watch_time = format_minutes(event['public_info'].get('totalTimeWatched', 0) / 60)

    email_body = f"""From: {FROM_NAME} <{FROM_EMAIL if FROM_EMAIL else 'NOT_SET'}>
To: {TO_EMAIL if TO_EMAIL else 'NOT_SET'}
Subject: {EMAIL_SUBJECT_PREFIX} {event['name']}

Event: {event['name']}

Unique Viewers: {int(event['public_info'].get('uniqueViewers', 0))}
Views: {int(event['public_info'].get('views', 0))}
New Viewers: {int(event['public_info'].get('newViewers', 0))}
Return Viewers: {int(event['public_info'].get('returnViewers', 0))}

Average Watch Time: {avg_watch_time}
Median Watch Time: {median_watch_time}
Total Watch Time: {total_watch_time}

Peak Concurrent Viewers: {int(event['public_info'].get('peakConcurrentViewers', 0))}

{city_breakdown}"""

    if not FROM_EMAIL or not TO_EMAIL:
        print(f"\n{'='*80}")
        print("Email sending disabled: FROM_EMAIL or TO_EMAIL not set")
        print(f"FROM_EMAIL: {FROM_EMAIL if FROM_EMAIL else 'NOT_SET'}")
        print(f"TO_EMAIL: {TO_EMAIL if TO_EMAIL else 'NOT_SET'}")
        print(f"{'='*80}")
        print("Would have sent the following email:")
        print(f"{'-'*80}")
        print(email_body)
        print(f"{'='*80}\n")
        return

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    if SMTP_USERNAME and SMTP_PASSWORD:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(FROM_EMAIL, TO_EMAIL, email_body)
    server.quit()




auth_request = requests.post(
    f"https://{API_HOSTNAME}/api/v3/login?newToken=true",
    json={"userName": USERNAME, "password": PASSWORD,},
)

auth_data = auth_request.json()
customer_id = auth_data["customerId"]
auth_token = auth_data["token"]

# Set up headers for authenticated requests
auth_headers = {"Authorization": f"X-Bearer {auth_token}"}

# Calculate date range for last 14 days
end_date = datetime.now()
start_date = end_date - timedelta(days=14)
start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")

# Get list of events from telemetry API
telemetry_base_url = "https://telemetry.resi.io/api/v1"
events_list_request = requests.get(
    f"{telemetry_base_url}/customers/{customer_id}/webevents/statistics/views/allEvents?startDate={start_date_str}&endDate={end_date_str}&viewAllData=false&destinationType=embed",
    headers=auth_headers,
)
events_list_request.raise_for_status()

if FILENAME in os.listdir(DIR):
    with open(os.path.join(DIR, FILENAME), "r") as f:
        data = json.loads(f.read())
else:
    data = {"events": []}

events_list = events_list_request.json()

# Get event names from historicalwebevents endpoint
event_ids = [e["eventId"] for e in events_list]
if event_ids:
    event_ids_params = "&".join([f"id={eid}" for eid in event_ids])
    # Use cookies for central.resi.io API
    historical_events_request = requests.get(
        f"https://{API_HOSTNAME}/api/v3/customers/{customer_id}/historicalwebevents?{event_ids_params}",
        cookies=auth_request.cookies,
    )
    historical_events_request.raise_for_status()
    historical_events = {e["webEventId"]: e for e in historical_events_request.json()}
else:
    historical_events = {}

new_uuids = []
for event_info in events_list:
    uuid = event_info["eventId"]
    if uuid in [e["event_id"] for e in data["events"]]:
        continue
    new_uuids.append(uuid)

    event_data = {}
    event_data["event_id"] = uuid
    event_data["start_time"] = event_info["date"]

    # Get event name from historical events
    if uuid in historical_events:
        event_data["name"] = historical_events[uuid]["name"]
    else:
        event_data["name"] = f"Event {uuid}"

    # Use the same broad date range for KPI requests (not the specific event times)
    telemetry_params = f"destinationType=embed&endDate={end_date_str}&startDate={start_date_str}&eventId={uuid}"

    # Fetch all the statistics from the telemetry API
    public_info = {}

    stats = [
        "uniqueViewers",
        "views",
        "avgWatchTime",
        "medianWatchTime",
        "totalTimeWatched",
        "newViewers",
        "returnViewers",
        "peakConcurrentViewers"
    ]

    for stat in stats:
        url = f"{telemetry_base_url}/customers/{customer_id}/kpis/{stat}?{telemetry_params}"
        response = requests.get(url, headers=auth_headers)
        response.raise_for_status()
        stat_data = response.json()
        # The API returns a list with a single object containing the value
        if isinstance(stat_data, list) and len(stat_data) > 0:
            public_info[stat] = stat_data[0].get("value", 0)
        else:
            public_info[stat] = 0

    # Convert avgWatchTime to minutes (assuming it's in seconds)
    if "avgWatchTime" in public_info:
        public_info["averageViewMinutes"] = public_info["avgWatchTime"] / 60

    # Convert totalTimeWatched to minutes (assuming it's in seconds)
    if "totalTimeWatched" in public_info:
        public_info["watchTimeMinutes"] = public_info["totalTimeWatched"] / 60

    event_data["public_info"] = public_info

    # Fetch city breakdown data
    city_params = f"eventAnalytics=viewers&segmentBy=none&eventId={uuid}&startDate={start_date_str}&endDate={end_date_str}&isFullMonth=false&destinationType=embed&viewAllData=false"
    city_url = f"{telemetry_base_url}/customers/{customer_id}/webevents/statistics/viewers/city?{city_params}"
    city_response = requests.get(city_url, headers=auth_headers)
    city_response.raise_for_status()
    city_data = city_response.json()

    # Sort locations by viewer count (highest to lowest)
    if "locations" in city_data:
        sorted_locations = sorted(
            city_data["locations"],
            key=lambda x: x["none"]["viewers"],
            reverse=True
        )
        event_data["city_data"] = sorted_locations
    else:
        event_data["city_data"] = []

    data["events"].append(event_data)


for event in data["events"]:
    # Only run the following code for new events
    if event["event_id"] not in new_uuids:
        continue

    # Only send emails for events with more than 5 viewers
    if event["public_info"]["uniqueViewers"] > 5:
        send_email(event)

with open(os.path.join(DIR, FILENAME), "w") as f:
    f.write(json.dumps(data, indent="  "))
