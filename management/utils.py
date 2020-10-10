import math
from datetime import date, datetime
from typing import Tuple

from dateutil import tz
from dateutil.easter import easter
from django.conf import settings


# months go from 1 .. 12 but % and // uses 0 .. 11 so the +1 / -1
def add_months(month, add):
    return (month + add - 1) % 12 + 1


def datetime_plus_months(d: date, months: int):
    return datetime(year=d.year + (d.month + months - 1) // 12, month=add_months(d.month, months), day=d.day,
                    tzinfo=tz.gettz(settings.TIME_ZONE))


def is_holiday(d: date) -> Tuple[bool, str]:
    # feste Feiertage
    if d.month == 5 and d.day == 1:
        return True, 'Tag der Arbeit'
    if d.month == 8 and d.day == 15:
        return True, 'Maria Himmerlfahrt'
    if d.month == 10 and d.day == 3:
        return True, 'Tag der Deutschen Einheit'
    if d.month == 11 and d.day == 1:
        return True, 'Allerheiligen'
    if (d.month == 12 and d.day >= 24) or (d.month == 1 and d.day <= 6):
        return True, 'Weihnachten'

    # Feiertage abhaengig von Ostern
    diff = d - easter(d.year)
    day_diff = int(math.floor(diff.total_seconds() / 86400))

    if day_diff == -2:
        return True, 'Karfreitag'
    if day_diff == 0:
        return True, 'Ostersonntag'
    if day_diff == 1:
        return True, 'Ostermontag'
    if day_diff == 39:
        return True, 'Christi Himmelfahrt'
    if day_diff == 49:
        return True, 'Pfingstsonntag'
    if day_diff == 50:
        return True, 'Pfingstmontag'
    if day_diff == 60:
        return True, 'Fronleichnam'

    return False, ''


def is_during_lecture_time(d: date) -> Tuple[bool, str]:
    end_of_ws = date(d.year, 2, 1)
    start_of_ss = date(d.year, 4, 1)
    end_of_ss = date(d.year, 8, 1)
    start_of_ws = date(d.year, 10, 1)

    today = date.today()

    if end_of_ws > today:
        return True, 'Wintersemester'
    if start_of_ss > today:
        return False, 'Vorlesungsfreie Zeit (Winter)'
    if end_of_ss > today:
        return True, 'Sommersemester'
    if start_of_ws > today:
        return False, 'Vorlesungsfreie Zeit (Sommer)'

    return True, 'Wintersemester'
