#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import re
import logging
import datetime
from datetime import date

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

    # patch today's price
    hist.sort(ascending=True, inplace=True) # 163 data is desending
    last = pandas.to_datetime(hist.ix[-1].name).date()
    today_here = date.today()
    dt = datetime.datetime.utcnow() + datetime.timedelta(seconds=8*60*60) # Beijing Time
    today_china = dt.date()
    if pandas.to_datetime(end).date() == today_here:
        if match_china and last != today_china:
            row = ntes.get_quote_today(code)
            if row:
                df = pandas.DataFrame(index=pandas.DatetimeIndex(start=today_china, end=today_china, freq="D"),
                                      columns=COLUMNS, dtype=float)
                df.ix[0] = Series(row)
                df["Volume"] = df["Volume"].astype(int)
                hist = hist.append(df)
        elif last != today_here:
            row = yhoo.get_quote_today(symbol)
            if row:
                df = pandas.DataFrame(index=pandas.DatetimeIndex(start=today_here, end=today_here, freq="D"),
                                      columns=COLUMNS, dtype=float)
                df.ix[0] = map(float, row[2:])
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
    hist = MyDataReader(symbol)
    print hist.tail()

    symbol = "300382.SZ"
    hist = MyDataReader(symbol)
    print hist.tail()

    symbol = "399006.SZ" # index
    hist = MyDataReader(symbol)
    print hist.tail()

    symbol = "600385.SS" # delisting
    hist = MyDataReader(symbol)
    print hist.tail()

    symbol = "AAPL"
    hist = MyDataReader(symbol)
    print hist.head()

