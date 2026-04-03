#!/usr/bin/env python3
"""
facebook_json_export_download_photos.py — Download photos from a Facebook JSON data export.

Reads a Facebook Takeout/export JSON file (posts or photo list) and downloads
the image files, organized into per-date subdirectories (photos/YYYY-MM-DD/).
Skips already-downloaded files. Preserves original timestamps via utime.

Supports two input modes:
  - Post list (default): reads posts[].attachments[].data[].media.image.src
  - Photo list (--is-photo-list): reads items[].source directly

Usage:
  python3 facebook_json_export_download_photos.py -f posts_1.json [OPTIONS]

Options:
  -f, --file FILE         Input JSON file (required)
  --output DIR            Directory to download photos into
  --since YYYY-MM-DD      Only download photos on/after this date (default: 2005-01-01)
  --until YYYY-MM-DD      Only download photos on/before this date
  --is-photo-list         Input is a flat photo list (source URL per item) not a post list
  --dry-run               Print URLs without downloading

Requirements: urllib3 (pip install urllib3)
"""
# Download Facebook photos that you are tagged in and that you uploaded

import os
import argparse
import urllib.request
import json

from datetime import datetime

import urllib3.util


# download photo
def download(uri, dirname, ts):
    """
    # update browser object with content from current url
    browser.get(browser.current_url)

    # find the relevant tag containing link to photo
    xpath_str = '''//script[contains( text( ), 'image":{"uri')]'''
    script_tag = get_element(browser, By.XPATH, xpath_str)
    if script_tag is None:
        if 'Temporarily Blocked' in browser.page_source:
            raise RuntimeError('Temporarily Blocked by FaceBook')
        print('ERROR: No image at {}'.format(browser.current_url))
        return False

    script_html = script_tag.get_attribute('innerHTML')

    # parse the tag for the image url
    html_search = re.search('"image":{"uri":"(?P<uri>.*?)"', script_html)
    uri = html_search.group('uri').replace('\\', '')
    """
    # determine file type and photo id
    # matches = re.search('(?P<photo_id>\w+)\.(?P<ext>\w+)\?', uri)
    # ext = matches.group('ext')
    # photo_id = matches.group('photo_id')

    # parse the tag for the image date
    # time_search = re.search('"created_time":(?P<timestamp>\d+)', script_html)
    # ts = int(time_search.group('timestamp'))
    # dt = datetime.utcfromtimestamp(ts).strftime('%Y%m%d')

    # create a filename for the image
    # filename_format = "photos/{date}_fb_{photo_id}.{ext}"
    # filename = filename_format.format(
    #     date=dt,
    #     photo_id=photo_id,
    #     ext=ext,
    # )
    link_path = urllib3.util.parse_url(uri).path
    link_filename = os.path.basename(link_path)
    os.makedirs(dirname, exist_ok=True)
    filename = f"{dirname}/{link_filename}"

    # check if already downloaded
    if os.path.isfile(filename):
        print("Photo {} already downloaded".format(filename))
        return True

    # download the image
    print("Downloading {}".format(uri))
    try:
        urllib.request.urlretrieve(uri, filename)
    except urllib.error.URLError as e:
        print("ERROR: Network error: {}".format(e))
        return False

    # set access and modified times
    os.utime(filename, (ts, ts))

    return True


def get_args():
    parser = argparse.ArgumentParser(description="Download photos from Facebook")
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        required=True,
        help="Input json file to get images from.",
    )
    parser.add_argument("--output", action="store", help="Directory to store photos")
    parser.add_argument("--since", action="store", default="2005-01-01", help="Date to start")
    parser.add_argument("--until", action="store", help="Date to end")
    parser.add_argument("--is-photo-list", action="store_true", help="Indicate the file is a photo list not a photo list")
    parser.add_argument("--dry-run", action="store_true", help="Dry run only do not download")
    args = parser.parse_args()
    return args


def process_attachments(attachments):
    urls = []
    for attachment in attachments:
        if "media" in attachment and "image" in attachment["media"]:
            media_url = attachment["media"]["image"]["src"]
            urls.append(media_url)
        if "subattachments" in attachment:
            subattachments = attachment["subattachments"]["data"]
            urls.extend(process_attachments(subattachments))
    return urls


def is_date_between(start_date, end_date, date_to_check):
    """
    Checks if a date falls between a start and end date (inclusive).

    Args:
        start_date (date): The start date of the range.
        end_date (date): The end date of the range.
        date_to_check (date): The date to check.

    Returns:
        bool: True if the date is within the range, False otherwise.
    """
    return start_date <= date_to_check <= end_date


def main():
    # jq '.[].attachments.data[].media.image.src
    args = get_args()
    date_format = "%Y-%m-%d"
    date_since = args.since
    datetime_since = datetime.strptime(date_since, date_format)
    since = datetime_since.timestamp()
    if args.until:
        date_until = args.until
        datetime_until = datetime.strptime(date_until, date_format)
    else:
        datetime_until = datetime.now()
    until = datetime_until.timestamp()
    with open(args.file) as fp:
        items = json.load(fp)
    if args.output:
        if not os.path.exists(args.output):
            os.makedirs(args.output)
        os.chdir(args.output)
    for p in items:
        dt = datetime.fromisoformat(p["created_time"])
        ts = int(dt.timestamp())
        date = dt.date()
        if not is_date_between(since, until, dt.timestamp()):
            continue
        dirname = f"photos/{date}"
        if args.is_photo_list:
            i = p.get('source')
            if args.dry_run:
                print(f"{date} {i}")
            else:
                download(i, dirname, ts)
        else:
            # Skip the posts that do not have attachemtns
            # other types are "photo" or "video" with attachments
            if p.get("type") in ["link", "status"]:
                continue
            attachments = p.get("attachments", {}).get("data", [])
            all_attachments = process_attachments(attachments)
            for i in all_attachments:
                if args.dry_run:
                    print(f"{date} {i}")
                else:
                    download(i, dirname, ts)


if __name__ == "__main__":
    main()
