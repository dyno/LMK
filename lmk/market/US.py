from os.path import join, exists
from datetime import date, datetime

from pytz import timezone
from dateutil.relativedelta import relativedelta, MO, TH

from ..utils import Singleton
from ..datasource.Yahoo import Yahoo
from ..datasource.Google import Google
from .Market import Market, TradeHour, TradeTime

@Singleton
class US(Market):
    tz = timezone("America/New_York")

    # http://www.nasdaq.com/about/trading-schedule.aspx
    #trading_hour = TradeHour(TradeTime(9, 30), TradeTime(16, 0))
    # force to retrieve today's price
    trading_hour = TradeHour(TradeTime(9, 30), TradeTime(21, 0))

    # http://en.wikipedia.org/wiki/Public_holidays_in_the_United_States
    holidays = []
    for year in range(2005, 2025):
        holidays.extend([
            # TODO: if holiday falls in weekend then ...
            date(year, 1, 1),                                               # New Year's Day
            (datetime(year, 1, 1) + relativedelta(weekday=MO(3))).date(),   # Martin Luther King, Jr.
            (datetime(year, 2, 1) + relativedelta(weekday=MO(3))).date(),   # Presidents' Day
            (datetime(year, 6, 1) + relativedelta(weekday=MO(-1))).date(),  # Memorial Day
            date(year, 7, 4),                                               # Independence Day
            (datetime(year, 9, 1) + relativedelta(weekday=MO(1))).date(),   # Labor Day
            (datetime(year, 10, 1) + relativedelta(weekday=MO(2))).date(),  # Columbus Day
            date(year, 11, 11),                                             # Veterans Day
            (datetime(year, 11, 1) + relativedelta(weekday=TH(4))).date(),  # Thanksgiving Day
            date(year, 12, 25),                                             # Christmas
        ])

    def __init__(self, name="US"):
        super().__init__()

        self.name = name

        self.datasources = {
            "yahoo" : Yahoo(),
            "google": Google(),
        }
        self.datasource = self.datasources["yahoo"]

