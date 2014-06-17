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


# ------------------------------------------------------------------------------
def adjust_close_price(hist, changes):
    changes = [(e[3], e) for e in changes]
    changes.sort()
    changes.reverse()
    changes = [e[1] for e in changes]

    hist["_Close"] = hist["Close"] # backup
    for stock_dividend, stock_issue, cash_dividend, _dt in changes:
        try: stock_dividend = int(stock_dividend)
        except: stock_dividend = 0
        try: stock_issue = int(stock_issue)
        except: stock_issue = 0
        try: cash_dividend = float(cash_dividend)
        except: cash_dividend = 0

        def c(r):
            # 1) only account for split, e.g. http://www.znz888.com/stock/history.php?code=sz300011&type=history
            #    10 * stock_price_before = (10 + stock_dividend + stock_issue) * stock_price_after
            #    yahoo seems to have adopt this method too.
            # 2) consider both split and dividend, e.g. google data.
            #    https://www.google.com/finance/historical?cid=9525130&startdate=Apr+1%2C+2014&enddate=Apr+30%2C+2014&num=30&ei=BmGgU9i1KsrniwLM3oCQDg
            #    10 * stock_price_before + cash_dividend = (10 + stock_dividend + stock_issue) * stock_price_after
            return  r["Close"] if r.name.strftime("%Y-%m-%d") >= _dt else \
                    (r["Close"] * 10 + cash_dividend) / (10 + stock_dividend + stock_issue)

        #hist.loc[hist.index < _dt, ["Adj Close",]] = hist.loc[hist.index < _dt].apply(c, axis=1)
        del hist["Adj Close"]; hist["Adj Close"] = hist.apply(c, axis=1)
        del hist["Close"]; hist["Close"] = hist["Adj Close"]

    del hist["Close"]; hist.rename(columns=lambda c: c.replace('_', ''), inplace=True) # restore


# ------------------------------------------------------------------------------
COLUMNS = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]
ptn_CHINA = re.compile(r"\d{6}")
def MyDataReader(symbol, start=None, end=None):
    start, end = _sanitize_dates(start, end)

    match_china = ptn_CHINA.search(symbol)
    if not match_china:
        hist = DataReader(symbol, "yahoo", start, end)
    else:
        # fallback to 163 data...
        hist = ntes.get_data(symbol, start=start, end=end)
        if ntes.is_stock(symbol):
            changes = ntes.get_stock_divident_split(symbol)
            adjust_close_price(hist, changes)

    hist.sort(ascending=True, inplace=True) # data might be desending, like 163

    # normalize the data
    # http://luminouslogic.com/how-to-normalize-historical-data-for-splits-dividends-etc.htm
    hist["_Open"] = hist["Open"] * hist["Adj Close"] / hist["Close"]
    hist["_High"] = hist["High"] * hist["Adj Close"] / hist["Close"]
    hist["_Low"] = hist["Low"] * hist["Adj Close"] / hist["Close"]
    hist["_Close"] = hist["Adj Close"]
    #print hist.tail(30)

    del hist["Open"], hist["High"], hist["Low"], hist["Close"]
    hist.rename(columns=lambda c: c.replace('_', ''), inplace=True) # restore

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
    import warnings
    from pandas.core.common import SettingWithCopyWarning
    warnings.simplefilter('error',SettingWithCopyWarning)

    import sys
    from common import probe_proxy
    probe_proxy()
    log.init(logging.DEBUG)

    # China Securities Regulatory Commission
    # http://www.csrc.gov.cn/pub/newsite/scb/ssgshyfljg/201401/W020140102326518754522.pdf # 行业分类

    symbol = "000001.SS"
    symbol = "600489.SS"
    symbol = "300011.SZ" # 鼎汉技术
    hist = MyDataReader(symbol, start="2014-04-01", end="2014-04-30")
    print hist.tail(20)

    sys.exit(0)

    symbol = "AAPL"
    hist = MyDataReader(symbol)
    print hist.tail(30)
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

