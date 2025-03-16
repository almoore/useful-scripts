from dateutil import parser
import pytz
from datetime import datetime

def parse_date_without_timezone(date_str):
    """Parse a date string without timezone information into a datetime object."""
    try:
        return parser.parse(date_str)
    except ValueError as e:
        print(f"Error parsing date: {e}")
        return None

def adjust_to_local_timezone(utc_datetime, local_tz):
    """Convert a UTC datetime object to a specified local timezone."""
    return utc_datetime.replace(tzinfo=pytz.utc).astimezone(local_tz)

def main():
    # Example date strings without timezone info
    date_str_utc = "2023-05-15 14:30:00"  # Assume this is in UTC
    date_str_local = "2023-05-15 10:30:00"  # Assume this needs to be local timezone

    # Parse the date strings
    utc_date = parse_date_without_timezone(date_str_utc)
    naive_local_date = parse_date_without_timezone(date_str_local)

    if utc_date and naive_local_date:
        # Correct the local date as if naive local time to current local time
        local_tz = pytz.timezone('America/New_York')  # Change this to your local timezone

        # Convert UTC datetime to local timezone to make fair comparison
        adjusted_utc_date = adjust_to_local_timezone(utc_date, local_tz)

        # Assume that naive_local_date is already in local timezone without explicit info
        localized_naive_date = local_tz.localize(naive_local_date)

        # Compare dates
        if adjusted_utc_date > localized_naive_date:
            print(f"{adjusted_utc_date} (UTC) is later than {localized_naive_date} (Local)")
        else:
            print(f"{localized_naive_date} (Local) is later than {adjusted_utc_date} (UTC)")
    else:
        print("Error in parsing dates.")
        
if __name__ == "__main__":
    main()

