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
DIR = secrets.DIR
# This is the name of the JSON file that you'd like to write to
FILENAME = secrets.FILENAME
# This is the username for your LA1 login
USERNAME = secrets.USERNAME
# This is the password for your LA1 login
PASSWORD = secrets.PASSWORD
# Email address from which you'd like to send viewer information
FROM_EMAIL = secrets.FROM_EMAIL
# Email address to which you'd like to send viewer information
TO_EMAIL = secrets.TO_EMAIL


def send_email(event):
    server = smtplib.SMTP("aspmx.l.google.com", 25)
    server.sendmail(
        FROM_EMAIL,
        TO_EMAIL,
        f"""From: Production Analytics <{FROM_EMAIL}>
To: {TO_EMAIL}
Subject: [Epic Production Analytics] {event['name']}, {event['start_time']}

Unique Viewers: {event['public_info']['totalViewers']}
Views: {event['public_info']['views']}""",
    )


def render_html_report(event):
    return template.render(
        name=event["name"],
        start_time=event["name"],
        event_id=event["name"],
        charts=[
            {
                "chart_type": "bar",
                "x": [city for (city, _) in city_client_info],
                "y": [data for (_, data) in city_client_info],
                "title": "Unique Clients Per City",
            },
            {
                "chart_type": "bar",
                "x": [city for (city, _) in city_ip_info],
                "y": [data for (_, data) in city_ip_info],
                "title": "Unique IPs Per City",
            },
            {
                "chart_type": "bar",
                "x": [resolution for (resolution, _) in resolution_client_info],
                "y": [data for (_, data) in resolution_client_info],
                "title": "Unique Clients Per Resolution",
            },
            {
                "chart_type": "bar",
                "x": [os for (os, _) in os_client_info],
                "y": [data for (_, data) in os_client_info],
                "title": "Unique Clients Per OS",
            },
            {
                "chart_type": "bar",
                "x": [browser for (browser, _) in browser_client_info],
                "y": [data for (_, data) in browser_client_info],
                "title": "Unique Clients Per Browser",
            },
            {
                "chart_type": "histogram",
                "x": watch_times,
                "y": "",
                "title": "Watch Times (mins)",
            },
        ],
        distinct_ips=len(set(ips)),
        distinct_clients=len(set(client_ids)),
    )


auth_request = requests.post(
    "https://central.livingasone.com/api/v3/login?newToken=true",
    json={"userName": USERNAME, "password": PASSWORD,},
)

customer_id = auth_request.json()["customerId"]
events_request = requests.get(
    f"https://central.livingasone.com/api/v3/customers/{customer_id}/webevents",
    cookies=auth_request.cookies,
)


if FILENAME in os.listdir(DIR):
    with open(os.path.join(DIR, FILENAME), "r") as f:
        data = json.loads(f.read())
else:
    data = {"events": []}

new_uuids = []
for event in [e for e in events_request.json()]:
    uuid = event["uuid"]
    if uuid in [e["event_id"] for e in data["events"]]:
        continue
    new_uuids.append(uuid)
    event_data = {}
    event_data["event_id"] = uuid
    event_data["start_time"] = event["startTime"]
    event_data["name"] = event["name"]

    public_info = requests.get(
        f"https://central.livingasone.com/api_v2.svc/public/events/{uuid}/status/rep?geoData=true"
    )
    event_data["public_info"] = public_info.json()

    detailed_info = requests.get(
        f"https://central.livingasone.com/api/v3/customers/{customer_id}/webevents/{uuid}/export?max=500",
        cookies=auth_request.cookies,
    )
    event_data["viewer_info"] = detailed_info.json()
    data["events"].append(event_data)


with open(os.path.join(DIR, FILENAME), "w") as f:
    f.write(json.dumps(data))


with open(os.path.join(DIR, "template.html"), "r") as f:
    template = Template(f.read())


def get_start_time(ts, watch_time_minutes):
    ts = ts[: ts.index(".")]
    date = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    return date - timedelta(minutes=watch_time_minutes)


for event in data["events"]:
    # Only run the following code for new events
    if event["event_id"] not in new_uuids:
        continue

    charts = []

    city_level = collections.defaultdict(list)
    resolution_level = collections.defaultdict(list)
    os_level = collections.defaultdict(list)
    browser_level = collections.defaultdict(list)
    ips = []
    client_ids = []
    watch_times = []
    start_times = []

    for info in event["viewer_info"]:
        city_level[f"{info['city']}, {info['state']}"].append(info)
        resolution_level[f"_{info['resolution']}"].append(info)
        os_level[
            f"{user_agent_parser.Parse(info['userAgent'])['os']['family']}"
        ].append(info)
        browser_level[
            f"{user_agent_parser.Parse(info['userAgent'])['user_agent']['family']}"
        ].append(info)
        client_ids.append(info["clientId"])
        ips.append(info["ipAddress"])
        watch_times.append(info["watchTimeMinutes"])
        start_times.append(
            datetime.strftime(
                get_start_time(info["timestamp"], info["watchTimeMinutes"]), "%H:%M:%S"
            )
        )

    city_client_info = sorted(
        [
            (city, len(set(v["clientId"] for v in viewer_list)))
            for city, viewer_list in city_level.items()
        ],
        key=lambda x: -x[1],
    )
    city_ip_info = sorted(
        [
            (city, len(set(v["ipAddress"] for v in viewer_list)))
            for city, viewer_list in city_level.items()
        ],
        key=lambda x: -x[1],
    )
    resolution_client_info = sorted(
        [
            (resolution, len(set(v["clientId"] for v in viewer_list)))
            for resolution, viewer_list in resolution_level.items()
        ],
        key=lambda x: -x[1],
    )
    os_client_info = sorted(
        [
            (os, len(set(v["clientId"] for v in viewer_list)))
            for os, viewer_list in os_level.items()
        ],
        key=lambda x: -x[1],
    )
    browser_client_info = sorted(
        [
            (browser, len(set(v["clientId"] for v in viewer_list)))
            for browser, viewer_list in browser_level.items()
        ],
        key=lambda x: -x[1],
    )

    # Do not send emails for Social Media events, since those have no
    # viewer information from LA1
    if "Social Media" not in event["name"]:
        send_email(event)

    with open(
        os.path.join(
            DIR,
            f"outputs/{event['name']}_{event['start_time']}_{event['event_id']}.html",
        ),
        "w",
    ) as f:
        f.write(render_html_report(event))

