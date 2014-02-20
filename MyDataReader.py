#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import re
import logging
import datetime
from datetime import date, timedelta

import pandas
from pandas.io.data import DataReader, _sanitize_dates
from pandas import Series

import yhoo
import ntes
import log

COLUMNS = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]


ptn_CHINA = re.compile(r"\d{6}")
def MyDataReader(symbol, start=None, end=None):
    start, end = _sanitize_dates(start, end)

    match_china = ptn_CHINA.search(symbol)
    if not match_china:
        hist = DataReader(symbol, "yahoo", start, end)

    else:
        # fallback to 163 data...
        code = match_china.group(0)
        if symbol.endswith("SS"):
            code = "0%s" % code
        elif symbol.endswith("SZ"):
            code = "1%s" % code

        hist = ntes.get_data(code, start=start, end=end)

    hist.sort(ascending=True, inplace=True) # data might be desending, like 163

    # patch today's price
    last = pandas.to_datetime(hist.ix[-1].name).date()
    dt_utc = datetime.datetime.utcnow()
    dt_beijing =  dt_utc + timedelta(seconds=8*60*60) # Beijing Time
    dt_newyork =  dt_utc - datetime.timedelta(seconds=4*60*60) # New York Time
    row_today = None
    if match_china:
        today = dt_beijing.date()
        _time = dt_beijing.time()
        get_quote_today = ntes.get_quote_today
    else:
        today = dt_newyork.date()
        _time = dt_newyork.time()
        get_quote_today = yhoo.get_quote_today

    if (timedelta(days=1) <= today - last <= timedelta(days=7)
            and _time > datetime.time(hour=9)):
        row_today = get_quote_today(symbol)
        row_today = Series(row_today) if row_today else None

    if not row_today is None:
        df = pandas.DataFrame(index=pandas.DatetimeIndex(start=today, end=today, freq="D"),
                              columns=COLUMNS, dtype=float)
        df.ix[0] = row_today
        # http://stackoverflow.com/questions/15891038/pandas-change-data-type-of-columns
        df["Volume"] = df["Volume"].astype(int)
        hist = hist.append(df)

    return hist


if __name__ == "__main__":
    import sys
    from common import probe_proxy
    probe_proxy()
    log.init(logging.DEBUG)

    # China Securities Regulatory Commission
    # http://www.csrc.gov.cn/pub/newsite/scb/ssgshyfljg/201401/W020140102326518754522.pdf # 行业分类

    symbol = "000001.SS"
    symbol = "600489.SS"
    hist = MyDataReader(symbol)
    print hist.tail()

    symbol = "AAPL"
    hist = MyDataReader(symbol)
    print hist.tail()

    sys.exit(0)


    symbol = "300382.SZ"
    hist = MyDataReader(symbol)
    print hist.tail()

    symbol = "399006.SZ" # index
    hist = MyDataReader(symbol)
    print hist.tail()

    symbol = "600385.SS" # delisting
    hist = MyDataReader(symbol)
    print hist.tail()


