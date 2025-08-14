from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import dateparser


def _parse_to_utc(
    date_str: str,
    *,
    languages=None,
    date_order: str | None = None,
    default_tz: str = 'UTC',
    relative_base: datetime | None = None,
    prefer_dates_from: str | None = None,
):
    """
    Helper to parse any date string as a timezone-aware datetime and
    normalize it to UTC. Raises ValueError on failure.
    """
    settings = {
        'RETURN_AS_TIMEZONE_AWARE': True,  # always produce aware datetimes
        'TIMEZONE': default_tz,            # used only if input has no tz
        'TO_TIMEZONE': 'UTC',              # normalize output to UTC
    }
    if date_order:
        settings['DATE_ORDER'] = date_order
    if relative_base is not None:
        settings['RELATIVE_BASE'] = relative_base
    if prefer_dates_from:
        settings['PREFER_DATES_FROM'] = prefer_dates_from

    dt = dateparser.parse(date_str, languages=languages, settings=settings)
    if dt is None:
        raise ValueError(f"Unable to parse date: {date_str!r}")
    return dt


def standardDateToTimestamp(date_str: str) -> int:
    # Generic parser: assume UTC if no tz in the string
    dt = _parse_to_utc(date_str, default_tz='UTC')
    return int(dt.timestamp())


def standardChineseDatetoTimestamp(date_str: str) -> int:
    # Generic Chinese parser: default to mainland China time
    dt = _parse_to_utc(date_str, languages=['zh'], default_tz='Asia/Shanghai')
    return int(dt.timestamp())


def TheCourtNewsDateToTimestamp(date_str: str) -> int:
    # Day-first sources; default to UTC unless you know the site’s local tz
    dt = _parse_to_utc(date_str, date_order='DMY', default_tz='UTC')
    return int(dt.timestamp())


def SingTaoDailyChineseDateToTimestamp(date_str: str) -> int:
    # Sing Tao (HK): default HKT, normalize to UTC
    cleaned = date_str.replace("發佈時間：", "").replace(" HKT", "").strip()
    dt = _parse_to_utc(cleaned, languages=['zh'], default_tz='Asia/Hong_Kong')
    return int(dt.timestamp())


def SCMPDateToTimestamp(date_str: str) -> int:
    # SCMP (HK): default HKT when tz missing
    cleaned = date_str.replace("Published:", "").strip()
    dt = _parse_to_utc(cleaned, default_tz='Asia/Hong_Kong')
    return int(dt.timestamp())


def NowTVDateToTimestamp(time_str: str) -> int:
    # Now TV (HK): relative times based on current HKT
    hk_now = datetime.now(ZoneInfo('Asia/Hong_Kong'))
    dt = _parse_to_utc(
        time_str,
        languages=['zh'],
        default_tz='Asia/Hong_Kong',
        relative_base=hk_now,
        prefer_dates_from='past'
    )
    return int(dt.timestamp())


def RTHKChineseDateToTimestamp(date_str: str) -> int:
    # Example: '2025-07-04 HKT 00:57'
    dt = _parse_to_utc(
        date_str,
        default_tz='Asia/Hong_Kong'
    )
    return int(dt.timestamp())


def IntiumChineseDateToTimestamp(date_str: str) -> int:
    # Initium (端傳媒): HK-based; default HKT
    cleaned = date_str.replace("刊登於", "").strip()
    dt = _parse_to_utc(cleaned, languages=['zh'], default_tz='Asia/Hong_Kong')
    return int(dt.timestamp())


def YahooNewsToTimestamp(date_str: str) -> int:
    # Yahoo often provides ISO 8601 with offset/Z; fall back to UTC if missing
    dt = _parse_to_utc(date_str, default_tz='UTC')
    return int(dt.timestamp())


def HKEJDateToTimestamp(date_str: str) -> int:
    # HKEJ: treat Chinese relative words with a Shanghai-based "now"
    sh_now = datetime.now(ZoneInfo('Asia/Shanghai'))

    # Preprocess common Chinese expressions to explicit dates in Shanghai time
    replacements = {
        "今日": sh_now.strftime("%Y-%m-%d"),
        "今天": sh_now.strftime("%Y-%m-%d"),
        "昨天": (sh_now - timedelta(days=1)).strftime("%Y-%m-%d"),
        "明天": (sh_now + timedelta(days=1)).strftime("%Y-%m-%d"),
    }
    for word, replacement in replacements.items():
        if word in date_str:
            date_str = date_str.replace(word, replacement)
            break

    dt = _parse_to_utc(
        date_str,
        languages=['zh'],
        default_tz='Asia/Shanghai',
        prefer_dates_from='past'
    )
    return int(dt.timestamp())

