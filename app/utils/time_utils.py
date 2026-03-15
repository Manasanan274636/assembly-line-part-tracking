from datetime import datetime, timedelta, timezone

def get_thai_now():
    """
    Returns the current time in Thailand (GMT+7).
    """
    # Create a timezone object for GMT+7
    thai_tz = timezone(timedelta(hours=7))
    return datetime.now(thai_tz).replace(tzinfo=None)

def get_thai_today():
    """
    Returns the current date in Thailand (GMT+7).
    """
    return get_thai_now().date()
