import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, UTC

import feedparser
import pytz
import requests
from ics import Calendar, Event

LOGGER = logging.getLogger(__name__)
FORMAT = "%(asctime)s - %(message)s"

ns = {'bc': 'http://bibliocommons.com/rss/1.0/modules/event/'}

def parse_dtstr(dtstr):
    utc_time = datetime.strptime(dtstr, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)
    return utc_time
    # local_time = utc_time.astimezone(pytz.timezone("America/Los_Angeles"))
    # return local_time

def fetch_events(url):
    LOGGER.info(f"retrieving url: {url}")
    response = requests.get(url)
    LOGGER.info("retrieved")
    
    if response.status_code != 200:
        print("Error fetching the RSS feed.")
        return
    
    root = ET.fromstring(response.content)
    
    # Find the 'channel' element, or directly handle top-level items
    channel = root.find("channel")
    if channel is None:
        print("Invalid RSS feed format.")
        return

    # print(channel.find('title').text)
    # print(channel.find('description').text)
    # print(channel.find('link').text)

    events = []
    # Loop through items (entries)
    for item in channel.findall("item"):  # Get the latest 5 entries
        title = item.find("title").text
        description = item.find("description").text
        link = item.find("link").text
        start_date = parse_dtstr(item.find("bc:start_date", ns).text)
        end_date = parse_dtstr(item.find("bc:end_date", ns).text)

        # Handle bc:location if it exists
        location = item.find("bc:location", ns)
        location_name = location.find("bc:name", ns).text if location is not None else ""
        
        
        # Extract all <category> tags
        categories = [category.text for category in item.findall("category")]
        categories_text = ", ".join(categories) if categories else "No categories"
        is_cancelled = item.find('bc:is_cancelled', ns).text
        for_babies = 'Kids: Babies' in categories
        for_toddlers = 'Kids: Toddlers' in categories
        for_families = 'Kids: Family Events' in categories
        if 'torytime' not in title and not for_babies and not for_toddlers and not for_families:
            continue
        if is_cancelled != 'false':
            continue
        if 'organ' in location_name or 'ilroy' in location_name:
            continue
        events.append({
            "title": title,
            "description": description,
            "link": link,
            "location": location_name,
            "start_date": start_date,
            "end_date": end_date,
            "categories": categories})
            
        # print(start_date.strftime("%a, %m/%d/%Y %H:%M"))
        # print(f"{title} @ {location_name}")
        # print()
        # print(f"Link: {link}")
        # print(f"Start Date: {start_date}")
        # print(f"End Date: {end_date}")
        # print(f"Description: {description}")
        # print(f"Categories: {categories_text}\n")
    return events

def get_events(pages=20):
    events = []
    for i in range(1, pages+1):
        rss_feed_url = f"https://gateway.bibliocommons.com/v2/libraries/sccl/rss/events?page={i}"
        events.extend(fetch_events(rss_feed_url))
    return events

def generate_ics(events):
    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//Google Inc//Google Calendar 70.9054//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:SCCL Baby Events (no Gilroy, no Morgan Hill)",
        "X-WR-TIMEZONE:America/Los_Angeles",
        "X-WR-CALDESC:Santa Clara County Library Baby Events",
    ]
    LAST_MODIFIED = "20250401T000000Z"
    DTSTAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    for event in events:
        dtstart = event['start_date'].strftime("%Y%m%dT%H%M%SZ")
        dtend = event['end_date'].strftime("%Y%m%dT%H%M%SZ")
        summary = event['title']
        location = event['location']
        description = event['description'].replace('\n', '\n ')
        url = event['link']
        uniq = dtstart+summary+location
        uid = hashlib.sha1(uniq.encode('utf8')).hexdigest()
        

        lines.append("BEGIN:VEVENT")
        lines.append(f"DTSTART:{dtstart}")
        lines.append(f"DTEND:{dtend}")
        lines.append(f"DTSTAMP:{DTSTAMP}")
        lines.append(f"UID:{uid}")
        lines.append(f"SUMMARY:{summary}")
        lines.append(f"LOCATION:{location}")
        lines.append(f"DESCRIPTION:{description}")
        lines.append(f"LAST-MODIFIED:{LAST_MODIFIED}")
        lines.append(f"CREATED:{LAST_MODIFIED}")
        lines.append("TRANSP:OPAQUE")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return '\n'.join(lines)

def main():
    import logging
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    events = get_events()
    cal = generate_ics(events)
    with open('sccl_baby_events.ics', 'w') as f:
        f.write(cal)

if __name__ == "__main__":
    main()
