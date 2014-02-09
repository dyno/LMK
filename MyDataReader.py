#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import time
import re
import csv
from urllib2 import urlopen
from datetime import date

import pandas
from pandas.io.data import DataReader, _sanitize_dates
from pandas.io.parsers import read_csv
from pandas.util.testing import _network_error_classes

# China Securities Regulatory Commission
# http://www.csrc.gov.cn/pub/newsite/scb/ssgshyfljg/201401/W020140102326518754522.pdf # 行业分类

COLUMNS=["Open", "High", "Low", "Close", "Volume", "Adj Close"]

## yahoo ##
# http://www.gummy-stuff.org/Yahoo-data.htm
TODAY_YAHOO_URL="http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=sd1ohgl1vl1"
def get_quote_today_yahoo(symbol):
    response = urlopen(TODAY_YAHOO_URL % symbol)
    reader = csv.reader(response, delimiter=",", quotechar='"')
    for row in reader:
        if row[0] == symbol and row[1] != "N/A":
            #print pandas.to_datetime(row[1]).date(), date.today()
            if pandas.to_datetime(row[1]).date() == date.today():
                return row

## 163 ##
_HISTORICAL_163_URL = "http://quotes.money.163.com/service/chddata.html?code=%s&start=%s&end=%s&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;VOTURNOVER;VATURNOVER"
# http://quotes.money.163.com/service/chddata.html?code=1000001&start=19910102&end=20140207&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP
def get_data_163(symbol=None, start=None, end=None, retry_count=3,
                    pause=0.001, adjust_price=False, ret_index=False,
                    chunksize=25, name=None):
    """
    Get historical data for the given symbol from 163.
    Date format is datetime

    Returns a DataFrame.
    """
    start, end = _sanitize_dates(start, end)

    url = _HISTORICAL_163_URL % (symbol, start.strftime('%Y%m%d'), end.strftime('%Y%m%d'))

    #def _retry_read_url(url, retry_count, pause, name):
    for _ in range(retry_count):
        time.sleep(pause)

        try:
            response = urlopen(url)
            #response = open("/Users/hfu/Downloads/000001.csv")
            rs = read_csv(response, encoding="GBK", index_col=0, parse_dates=True, skiprows=[0,])
            #日期,股票代码,名称,收盘价,最高价,最低价,开盘价,前收盘,涨跌额,涨跌幅,成交量,成交金额
            rs = rs[[u"开盘价", u"最高价", u"最低价", u"收盘价", u"成交量", u"收盘价"]]
            rs.columns = COLUMNS
            return rs
        except _network_error_classes, e:
            print e

    raise IOError("after %d tries, %s did not "
                  "return a 200 for url %r" % (retry_count, name, url))


## main ##
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

        hist = get_data_163(symbol=code, start=start, end=end)

    # patch today's price
    hist.sort(ascending=True, inplace=True) # 163 data is desending
    last = pandas.to_datetime(hist.ix[-1].name).date()
    today = date.today()
    if pandas.to_datetime(end).date() == today and last != today:
        row = get_quote_today_yahoo(symbol)
        if row:
            df = pandas.DataFrame(index=pandas.DatetimeIndex(start=today, end=today, freq="D"),
                                  columns=COLUMNS, dtype=float)
            df.ix[0] = map(float, row[2:])
            # http://stackoverflow.com/questions/15891038/pandas-change-data-type-of-columns
            df["Volume"] = df["Volume"].astype(int)
            hist = hist.append(df)

    return hist

if __name__ == "__main__":
    from common import probe_proxy
    probe_proxy()

    symbol = "000001.SS"
    hist = MyDataReader(symbol)
    print hist.head()

    symbol = "AAPL"
    hist = MyDataReader(symbol)
    print hist.head()

