from datetime import datetime,timedelta
import dateparser

def standardDateToTimestamp(date_str: str):
    date_obj = dateparser.parse(date_str)
    return int(date_obj.timestamp())


def standardChineseDatetoTimestamp(date_str: str) -> int:
    dt = dateparser.parse(date_str, languages=['zh'])
    if dt is None:
        raise ValueError("Invalid Chinese date")
    return int(dt.timestamp())

def TheCourtNewsDateToTimestamp(date_str: str):
    date_obj = dateparser.parse(date_str, settings={'DATE_ORDER': 'DMY'})
    return int(date_obj.timestamp())


def SingTaoDailyChineseDateToTimestamp(date_str):
    date_str = date_str.replace("發佈時間：", "").replace(" HKT", "")
    dt = dateparser.parse(date_str, languages=['zh'], settings={'TIMEZONE': 'Asia/Hong_Kong', 'RETURN_AS_TIMEZONE_AWARE': True})
    if dt is None:
        raise ValueError("Invalid SingTao date")
    return int(dt.timestamp())

def SCMPDateToTimestamp(date_str):
    date_str = date_str.replace("Published:", "").strip()
    dt = dateparser.parse(date_str, settings={'TIMEZONE': 'Asia/Hong_Kong', 'RETURN_AS_TIMEZONE_AWARE': True})
    if dt is None:
        raise ValueError("Invalid SCMP date")
    return int(dt.timestamp())


def NowTVDateToTimestamp(time_str):
    dt = dateparser.parse(time_str, languages=['zh'], settings={'RELATIVE_BASE': datetime.now()})
    if dt is None:
        raise ValueError("Invalid NowTV time format")
    return int(dt.timestamp())
    

def RTHKChineseDateToTimestamp(date_str):
    """
    Parses a datetime string like '2025-07-04 HKT 00:57'
    and returns the Unix timestamp (int).
    """
    dt = dateparser.parse(
        date_str,
        settings={
            'TIMEZONE': 'Asia/Hong_Kong',
            'RETURN_AS_TIMEZONE_AWARE': True
        }
    )
    if dt is None:
        raise ValueError("Invalid date format")
    return int(dt.timestamp())

def IntiumChineseDateToTimestamp(date_str):
    # Parse the date string into a datetime object
    date_str = date_str.replace("刊登於", "").strip()
    datetime_obj = dateparser.parse(date_str)
    
    if datetime_obj is None:
        raise ValueError(f"Could not parse date: {date_str}")
    
    # Convert to Unix timestamp (UTC)
    return datetime_obj.timestamp()


def HKEJDateToTimestamp(date_str: str):
    # Preprocess common Chinese expressions
    replacements = {
        "今日": datetime.now().strftime("%Y-%m-%d"),
        "今天": datetime.now().strftime("%Y-%m-%d"),
        "昨天": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "明天": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
    }

    for word, replacement in replacements.items():
        if word in date_str:
            date_str = date_str.replace(word, replacement)
            break  # Only replace the first match

    # Parse with dateparser
    dt = dateparser.parse(
        date_str,
        languages=['zh'],
        settings={
            'PREFER_DATES_FROM': 'past',
            'TIMEZONE': 'Asia/Shanghai',
            'RETURN_AS_TIMEZONE_AWARE': True,
        }
    )

    if dt is None:
        raise ValueError(f"Could not parse date from input: {date_str}")

    return int(dt.timestamp())



