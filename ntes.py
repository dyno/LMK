#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import time
import sys
import re
import operator
import logging
import json
import datetime
import csv
from urllib2 import urlopen, HTTPError
from datetime import date
from StringIO import StringIO
from HTMLParser import HTMLParser

import pandas
from pandas.util.testing import _network_error_classes
from pandas.io.parsers import read_csv
from pandas.io.data import DataReader, _sanitize_dates
from pandas import Series

import log
import MyDataReader
from common import fmt_err_msg


#http://quotes.money.163.com/service/dadan_data.html?symbol=300382&amount=500000&page=0
DADAN_DATA_163_URL = "http://quotes.money.163.com/service/dadan_data.html?symbol=%s"
def _get_quote_today_dadan(symbol):
    class MyHTMLParser(HTMLParser):
        def __init__(self, *argv, **kargs):
            HTMLParser.__init__(self, *argv, **kargs)
            self.entry_start = False

            self.td_count = 0
            self.prices = []
            self.volumes = []

        def handle_starttag(self, tag, attrs):
            if tag == "tr":
                self.entry_start = True
                self.td_count = 0

            if tag == "td":
                self.td_count += 1

        def handle_endtag(self, tag):
            if tag == "tr":
                self.entry_start = False

        def handle_data(self, data):
            data = data.strip().replace(",", "")
            if self.entry_start and data:
                if self.td_count == 2:    # 成交价
                    self.prices.append(float(data))
                elif self.td_count == 3:    # 成交量
                    self.volumes.append(int(data))

    url = DADAN_DATA_163_URL % symbol
    log.logger.debug("get_quote_today_163(): '%s'", url)
    try:
        response = urlopen(url)
        data = json.load(response)
        parser = MyHTMLParser()
        parser.feed(data["dadan_table"])
        if len(parser.prices) > 0:
            return { "Open" : parser.prices[-1],
                     "High" : max(parser.prices),
                     "Low"  : min(parser.prices),
                     "Close": parser.prices[0],
                     "Volume": sum(parser.volumes),
                     "Adj Close" : sum(map(operator.mul, parser.prices, parser.volumes)) / sum(parser.volumes)
                    }
    except HTTPError, e:
        log.logger.debug("open '%s' result error.\n%s", url, e)


API_MONEY_126_URL = "http://api.money.126.net/data/feed/%s,money.api"
def _get_quote_today_126(code):
    url = API_MONEY_126_URL % code
    log.logger.debug("get_quote_today_126(): '%s'", url)
    try:
        response = urlopen(url)
        data = response.read()
        start, end = data.find("(") + 1, data.find(")")
        data = data[start:end]
        data = json.loads(data)[code]
        return { "Open" : data["open"],
                 "High" : data["high"],
                 "Low"  : data["low"],
                 "Close": data["yestclose"] + data["updown"],
                 "Volume": data["volume"] / 100,
                 "Adj Close" : data["yestclose"] + data["updown"],
                }
    except HTTPError, e:
        log.logger.debug("open '%s' result error.\n%s", url, e)


#-----------------------------------------------------------------------
## public ##

def get_quote_today(code, source="126"):
    if source == "126":
        return _get_quote_today_126(code)
    elif source == "163":
        return _get_quote_today_dadan(code)


_HISTORICAL_163_URL = "http://quotes.money.163.com/service/chddata.html?code=%s&start=%s&end=%s&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;VOTURNOVER;VATURNOVER"
# http://quotes.money.163.com/service/chddata.html?code=1000001&start=19910102&end=20140207&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER;TCAP;MCAP
def get_data(code=None, start=None, end=None, retry_count=3,
                    pause=0.001, adjust_price=False, ret_index=False,
                    chunksize=25, name=None):
    start, end = _sanitize_dates(start, end)

    url = _HISTORICAL_163_URL % (code, start.strftime('%Y%m%d'), end.strftime('%Y%m%d'))

    #def _retry_read_url(url, retry_count, pause, name):
    for _ in range(retry_count):
        time.sleep(pause)

        try:
            log.logger.debug("get_data(): url='%s'", url)
            response = urlopen(url)

            # debugging code
            #f = open("/tmp/%s.csv" % code, "w")
            #f.write(response.read())
            #f.close()
            #sys.exit(0)
            #response = open("/tmp/%s.csv" % code)

            # skip empty lines in head
            sio = StringIO(response.read())
            sio.seek(0, 0)
            while True:
                c = sio.read(1)
                if not c.isspace(): break
            sio.seek(-1, 1)

            rs = read_csv(sio, encoding="GBK", index_col=0, parse_dates=True)
            #日期,股票代码,名称,收盘价,最高价,最低价,开盘价,前收盘,涨跌额,涨跌幅,成交量,成交金额
            rs = rs[[u"开盘价", u"最高价", u"最低价", u"收盘价", u"成交量", u"收盘价"]]
            rs.columns = MyDataReader.COLUMNS
            return rs
        except _network_error_classes, e:
            log.logger.debug("get_data(): '%s' error:\n%s", url, fmt_err_msg(e))

    raise IOError("after %d tries, %s did not return a 200 for url %r" % (retry_count, name, url))


STOCK_SEARCH_URL = "http://quotes.money.163.com/stocksearch/json.do?count=10&word=%s"
def search_stock(symbol):
    if re.search("\d{6}", symbol):
        code = symbol[:6]
        type = "SH" if symbol[-2:] == "SS" else "SZ"
    else:
        code = symbol
        type = "US"

    url = STOCK_SEARCH_URL % code
    log.logger.debug("search_stock(): '%s'", url)
    try:
        response = urlopen(url)
        data = response.read()
        start, end = data.find("(") + 1, data.find(")")
        data = data[start:end]
        data = json.loads(data)
        for stk in data:
            if stk["type"] == type:
                return stk
    except HTTPError, e:
        log.logger.debug("open '%s' result error.\n%s", url, fmt_err_msg(e))


if __name__ == "__main__":
    import common
    common.probe_proxy()
    log.init()

    symbol = "300077.SZ"
    code = "1%s" % (symbol[:6], )

    hist = get_data(code)
    print hist.head()
    print hist.tail()

    quote = get_quote_today(code)
    print quote

    quote = get_quote_today(code, source="163")
    print quote

    stk = search_stock(symbol)
    print stk["name"]

    symbol = "TSLA"
    stk = search_stock(symbol)
    print stk["symbol"], stk["name"]


