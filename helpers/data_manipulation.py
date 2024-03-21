import datetime

def transform_timestamp_to_date(timestamp):
    return datetime.datetime.fromtimestamp(timestamp / 1000.0).strftime('%Y-%m-%d %H:%M:%S')