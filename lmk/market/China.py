import json
from os.path import join, exists
from datetime import date

from pytz import timezone

from ..utils import Singleton
from ..config import CACHE_DIR
from ..datasource.NetEase import NetEase
from .Market import Market, TradeHour, TradeTime

@Singleton
class China(Market):
    tz = timezone("Asia/Shanghai")

    # www.sse.com.cn/marketservices/investors/home/trading/c/51544.shtml
    #trading_hour = TradeHour(TradeTime(9, 30), TradeTime(15, 0))
    # force to retrieve today's price
    trading_hour = TradeHour(TradeTime(9, 30), TradeTime(18, 0))

    # http://en.wikipedia.org/wiki/Public_holidays_in_China
    # http://wannianrili.51240.com/
    # XXX: any python library for it? e.g. https://pypi.python.org/pypi/LunarSolarConverter/
    holidays = [
        date(2014, 1, 1),  # New 2014's Day
        date(2014, 1, 31), # Chinese New 2014
        date(2014, 2, 1),  # Chinese New 2014
        date(2014, 2, 2),  # Chinese New 2014
        date(2014, 2, 3),  # Chinese New 2014
        date(2014, 2, 4),  # Chinese New 2014
        date(2014, 2, 5),  # Chinese New 2014
        date(2014, 2, 6),  # Chinese New 2014
        date(2014, 4, 7),  # Qingming Festival
        date(2014, 5, 1),  # Labour Day
        date(2014, 5, 2),  # Labour Day
        date(2014, 5, 3),  # Labour Day
        date(2014, 6, 2),  # Dragon Boat Festival
        date(2014, 9, 8),  # Mid-Autumn Festival
        date(2014, 10, 1), # National Day

        date(2015, 1, 1),  # New 2015's Day
        date(2015, 1, 2),  # New 2015's Day
        date(2015, 2, 18), # Chinese New 2015
        date(2015, 2, 19), # Chinese New 2015
        date(2015, 2, 20), # Chinese New 2015
        date(2015, 2, 23), # Chinese New 2015
        date(2015, 2, 24), # Chinese New 2015
        date(2015, 4, 6),  # Qingming Festival
        date(2015, 5, 1),  # Labour Day
        date(2015, 6, 22), # Dragon Boat Festival
        date(2015, 9, 4),  # Victory Over Japan Day
        date(2015, 9, 5),  # Victory Over Japan Day
        date(2015, 10, 1), # National Day
        date(2015, 10, 2), # National Day
        date(2015, 10, 5), # National Day
        date(2015, 10, 6), # National Day
        date(2015, 10, 7), # National Day

        date(2016, 1, 1),  # New 2016's Day
        date(2016, 2, 19), # Chinese New 2016
        date(2016, 2, 8),  # Chinese New 2016
        date(2016, 2, 9),  # Chinese New 2016
        date(2016, 2, 10), # Chinese New 2016
        date(2016, 2, 11), # Chinese New 2016
        date(2016, 2, 12), # Chinese New 2016
        date(2016, 4, 4),  # Qingming Festival
        date(2016, 5, 2),  # Labour Day
        date(2016, 6, 9),  # Dragon Boat Festival
        date(2016, 6, 10), # Dragon Boat Festival
        date(2016, 9, 15), # Mid-Autumn Festival
        date(2016, 9, 16), # Mid-Autumn Festival
        date(2016, 10, 3), # National Day
        date(2016, 10, 4), # National Day
        date(2016, 10, 5), # National Day
        date(2016, 10, 6), # National Day
        date(2016, 10, 7), # National Day
    ]

    def __init__(self, name="China"):
        super().__init__()

        self.name = name

        self.datasources = { "netease": NetEase() }
        self.datasource = self.datasources["netease"]

        self.name_cache = {}
        cache_file = join(CACHE_DIR, "name.cache.%s" % self.name)
        if exists(cache_file):
            with open(cache_file) as f:
                self.name_cache = json.load(f)

