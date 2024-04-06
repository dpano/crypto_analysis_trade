import datetime

def transform_timestamp_to_date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp / 1000.0).strftime('%Y-%m-%d %H:%M:%S')

def current_datetime():
    # Get the current date and time
    current_date_time = datetime.datetime.now()

    # Format the date and time as a string
    formatted_date_time = current_date_time.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_date_time