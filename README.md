[LA1 Analytics Scraper](https://github.com/epicsf/la1-analytics-scraper)
================================================================================

A Python script for downloading, storing, and emailing event analytics from Living As One.

Our motivation was to store this data locally for our records, and maintain access after the LA1 event expires along with its the analytics data. We also wanted an automated way to email viewership statistics to relevant folks (admins, leadership) after each event.


## Setup

We assume that you already have `python3` and `virtualenv` installed and that you have cloned or downloaded this repo.

1. Run `pip3 install -r requirements.txt` to download the dependencies for this script.
2. Make a copy of `example_secrets.py` named `secrets.py` and add your login credentials, to/from email address, and other config info.


## Usage

You can either run this script manually from your terminal (`python script.py`), or if you want to run it automatically you can use `cron` or any other scheduler.

Upon running it will write its outputs into your specified directory (`./outputs/` by default). It will create:

1. A single JSON file to cumulatively store detailed event analytics data. This gets appended to with each run (each new event) and also serves as a database for the script to keep track of which events have already been downloaded and emailed. This makes the script safe to run as often as you like.

2. Multiple HTML files (one for each event) with the summary analytics and some charts summarizing the detailed analytics (screenshot below).

3. An email with the subject prefix, to address, and from address specified in your config file, containing the summary analytics for each event.


## Screenshots

### Summary Email

<img width="739" alt="Summary email screenshot" src="https://user-images.githubusercontent.com/21501/75594270-087aec80-5a3d-11ea-9bd8-8fc2dbd4c6ef.png">

### HTML file output with data visualizations

<img alt="HTML file screenshot" src="https://user-images.githubusercontent.com/21501/75594296-13358180-5a3d-11ea-83a1-00f5909c9134.png">


## Caveats

### Viewer count discrepancies

You will likely see different numbers in the email summary than in the HTML file output. We draw the summary data from the LA1 event "Summary" CSV and build the HTML file from the LA1 event "Detailed Report" CSV. The discrepancies occur because the way LA1 calculates the summary data seems to be different from how we compute the viewer and unique viewer count from the detailed analytics. We're not doing anything fancy, merely counting up the lines in the detailed report and counting the unique IPs. Possibly LA1 is doing something more advanced for their counts, or there's a bug somewhere.

We've also noticed discrepancies over time, i.e. the viewer counts don't seem to be static after the event ends. We've seen them continue to increment up in the days/weeks after. We don't allow re-playing our events so it's unclear why this would be.

### SMTP Server
In the `send_email` function, we currently use [Gmail's Restricted SMTP Server](https://support.google.com/a/answer/176600?hl=en) to send email without having to provide any email login information, however this means the script can only send emails to Gmail or G Suite accounts. You can change these settings to your organization's SMTP server if you have one.

### Excluded Events
Streams to Facebook and YouTube and test events do not generally have useful analytics information, so we exclude events with fewer than 5 viewers from the summary email. Their data will still be written to the JSON file.

### LA1 API Limits
In one of the API requests we make to LA1, there is a `max=500` URL parameter. It's unclear whether that refers to the number of events returned or the number of detailed viewer analytics entries. If you have a large number of events or viewers, you should check to see that your data is not being truncated by this.


## Contributing

Issues, comments, and pull requests all welcome. [Find us on GitHub](https://github.com/epicsf).
