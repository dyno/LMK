#!/usr/bin/python
# vim: set fileencoding=utf-8 :

import urllib2
import sys
import shelve
import re
import pylab
import pandas
import operator
import math
import logging
import json
import csv

from urllib2 import urlopen, HTTPError
from pytz import timezone
from pandas.io.data import DataReader, _sanitize_dates
from pandas import HDFStore
from os.path import join, exists
from numpy import ma
from matplotlib.ticker import FuncFormatter
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY, FRIDAY
from matplotlib import pyplot as plt
from dateutil.relativedelta import relativedelta, MO, TH
from datetime import datetime, date, timedelta
from collections import namedtuple
from StringIO import StringIO
from HTMLParser import HTMLParser

import warnings
from pandas.core.common import SettingWithCopyWarning
warnings.simplefilter('error',SettingWithCopyWarning)

pandas.set_option('display.max_columns', 500)
pandas.set_option('display.width', 200)
plt.rcParams['figure.figsize'] = (19, 6)

#===============================================================================
# Convienction:
# * _env is global
# * for date variable, _dt is string, dt is datetime.date
# * symbols follow Yahoo Finance's format
# * it might be better implement as a module, but here we will use class as
#   namespace, like PivotCalculator

#===============================================================================
#http://legacy.python.org/dev/peps/pep-0318/#examples
def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

#===============================================================================
@singleton
class Environment(object):
    tz = timezone("America/Los_Angeles")

    def init_log(self, loglevel=logging.DEBUG):
        logging.basicConfig(level=loglevel, format="%(message)s")
        stdoutStreamHandler = logging.StreamHandler(stream=sys.stdout)

        self.logger = logging.getLogger()
        self.logger.setLevel(loglevel)

    def probe_proxy(self):
        use_proxy = False
        with open("/etc/resolv.conf") as resolv:
            for line in resolv:
                if line.find(".com") != -1:
                    use_proxy = True

        if not use_proxy:
            proxy_handler = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_handler)
            urllib2.install_opener(opener)

        return use_proxy

    @property
    def _today(cls):
        return date.today().strftime("%Y-%m-%d")

    @property
    def today(self):
        return date.today()

    @property
    def now(self):
        return datetime.now(tz=self.tz)

_env = Environment()
_env.init_log(loglevel=logging.DEBUG)
_env.probe_proxy()

#===============================================================================
class DataSource(object):
    def get_symbol_name(self, symbol):
        raise NotImplementedError()

    def retrieve_history(self, symbol, _start, _end):
        raise NotImplementedError()

    def get_quote_today(self, symbol):
        raise NotImplementedError()

#===============================================================================
@singleton
class Yahoo(DataSource):
    #---------------------------------------------------------------------------
    def get_symbol_name(self, symbol):
        return symbol

    #---------------------------------------------------------------------------
    def retrieve_history(self, symbol, _start, _end):
        return DataReader(symbol, "yahoo", _start, _end)

    #---------------------------------------------------------------------------
    # http://www.gummy-stuff.org/Yahoo-data.htm
    QUOTE_TODAY_URL = "http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=sd1ohgl1vl1c"
    def get_quote_today(self, symbol):
        url = self.QUOTE_TODAY_URL % symbol
        _env.logger.debug("get_quote_today(): '%s'", url)
        try:
            response = urlopen(url)
            reader = csv.reader(response, delimiter=",", quotechar='"')
            for row in reader:
                if row[0] == symbol and row[1] != "N/A":
                    #print pandas.to_datetime(row[1]).date(), date.today()
                    if pandas.to_datetime(row[1]).date() == date.today():
                        _env.logger.info("get_quote_today(): %s => price: %s, updown: %s",
                                        row[0], row[5], row[8].replace(" - ", ", "))
                        return {"Open"      : float(row[2]),
                                "High"      : float(row[3]),
                                "Low"       : float(row[4]),
                                "Close"     : float(row[5]),
                                "Volume"    : int(row[6]) if int(row[6]) > 0 else 1, # index has no volume...
                                "Adj Close" : float(row[5]),
                               }
        except HTTPError, e:
            _env.logger.debug("open '%s' result error.\n%s", url, e)

#===============================================================================
@singleton
class NetEase(DataSource):
    #---------------------------------------------------------------------------
    def _code7(self, symbol):
        if symbol.endswith(".SS"):
            code7 = "0%s" % symbol[:6]
        elif symbol.endswith(".SZ"):
            code7 = "1%s" % symbol[:6]
        else:
            raise Exception("I donnot have data for symbol '%s'. - NetEase")

        return code7

    def _code_type(self, symbol):
        if re.search("\d{6}", symbol):
            code = symbol[:6]
            _type = "SH" if symbol[-2:] == "SS" else "SZ"
        else:
            code = symbol
            _type = "US"

        return code, _type

    def _get_symbol_type(self, symbol):
        if symbol.endswith(".SS") and symbol[:3] in ("600", "601", "900"):
            return "stock"
        if symbol.endswith(".SZ") and symbol[:3] in ("000", "200", "002", "300"):
            return "stock"

        return "index"

    #---------------------------------------------------------------------------
    STOCK_SEARCH_URL = "http://quotes.money.163.com/stocksearch/json.do?count=10&word=%s"
    def get_symbol_name(self, symbol):
        code, _type = self._code_type(symbol)

        url = self.STOCK_SEARCH_URL % code
        _env.logger.debug("get_symbol_name(): '%s'", url)
        try:
            response = urlopen(url)
            data = response.read()
            start, end = data.find("(") + 1, data.find(")")
            data = data[start:end]
            data = json.loads(data)
            for stk in data:
                if stk["type"] == _type:
                    return stk["name"]
        except HTTPError, e:
            _env.logger.debug("open '%s' result error.\n%s", url, fmt_err_msg(e))


    #---------------------------------------------------------------------------
    # http://quotes.money.163.com/f10/fhpg_000001.html#01d05a
    FHPG_URL = "http://quotes.money.163.com/f10/fhpg_%s.html#01d05a"
    def get_split_history(self, symbol):
        class MyHTMLParser(HTMLParser):
            def __init__(self, *argv, **kargs):
                HTMLParser.__init__(self, *argv, **kargs)
                self.result = []

                self.in_h1 = False
                self.ds_start = False
                self.in_td = False

            def handle_starttag(self, tag, attrs):
                if tag == "h1":
                    self.ds_start = False
                    self.in_h1 = True

                if tag == "tr":
                    self.td_count = 0

                if tag == "td":
                    self.in_td = True
                    self.td_count += 1

            def handle_endtag(self, tag):
                if tag == "h1":
                    self.in_h1 = False
                if tag == "td":
                    self.in_td = False

            def handle_data(self, data):
                data = data.strip()
                if self.in_h1 and data.find(u"分红配股") != -1:
                    self.ds_start = True

                #print self.ds_start, self.in_td, data
                if self.ds_start and self.in_td and data:
                    if self.td_count == 3:  # 送股
                        self.record = []
                        self.record.append(data)
                    elif self.td_count == 4:# 转增
                        self.record.append(data)
                    elif self.td_count == 5:# 派息
                        self.record.append(data)
                    elif self.td_count == 7:# 除权除息日
                        self.record.append(data)
                        self.result.append(self.record)

        #-----------------------------------------------------------------------
        code = symbol[:6]
        url = self.FHPG_URL % code
        _env.logger.debug("get_split_history(): '%s'", url)
        try:
            response = urlopen(url)
            data = response.read().decode("utf-8")
            parser = MyHTMLParser()
            parser.feed(data)
            if len(parser.result) > 0:
                return parser.result
        except HTTPError, e:
            _env.logger.debug("open '%s' result error.\n%s", url, e)

    #---------------------------------------------------------------------------
    def adjust_close_price(self, history, split_history):
        split_history = [(e[3], e) for e in split_history]
        split_history.sort()
        split_history.reverse()
        split_history = [e[1] for e in split_history]

        history["_Close"] = history["Close"].copy() # backup
        for stock_dividend, stock_issue, cash_dividend, dt in split_history:
            try: stock_dividend = int(stock_dividend)
            except: stock_dividend = 0
            try: stock_issue = int(stock_issue)
            except: stock_issue = 0
            try: cash_dividend = float(cash_dividend)
            except: cash_dividend = 0
            # split is in future, no adjust is necessary.
            if dt > _env._today: continue

            def c(r):
                # 1) only account for split, e.g. http://www.znz888.com/stock/history.php?code=sz300011&type=history
                #    10 * stock_price_before = (10 + stock_dividend + stock_issue) * stock_price_after
                #    yahoo seems to have adopt this method too.
                # 2) consider both split and dividend, e.g. google data.
                #    https://www.google.com/finance/historical?cid=9525130&startdate=Apr+1%2C+2014&enddate=Apr+30%2C+2014&num=30&ei=BmGgU9i1KsrniwLM3oCQDg
                #    10 * stock_price_before + cash_dividend = (10 + stock_dividend + stock_issue) * stock_price_after
                return  r["Close"] if r.name.strftime("%Y-%m-%d") >= dt else \
                        (r["Close"] * 10 + cash_dividend) / (10 + stock_dividend + stock_issue)

            #hist.loc[hist.index < _dt, ["Adj Close",]] = hist.loc[hist.index < _dt].apply(c, axis=1)
            history["Adj Close"] = history.apply(c, axis=1)
            history["Close"] = history["Adj Close"]

	del history["Close"]; history.rename(columns=lambda c: c.replace('_', ''), inplace=True) # restore

    #---------------------------------------------------------------------------
    HISTORY_DATA_URL = "".join(["http://quotes.money.163.com/service/chddata.html?",
                                "code=%s&start=%s&end=%s&",
                                "fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;VOTURNOVER;VATURNOVER",
                               ])
    def retrieve_history(self, symbol, _start, _end):
        start, end = _sanitize_dates(_start, _end)
        code = self._code7(symbol)

        url = self.HISTORY_DATA_URL % (code, start.strftime('%Y%m%d'), end.strftime('%Y%m%d'))
        try:
            _env.logger.debug("retrieve_history(): url='%s'", url)
            response = urlopen(url)

            # skip empty lines in head
            sio = StringIO(response.read())
            sio.seek(0, 0)
            while True:
                c = sio.read(1)
                if not c.isspace(): break
            sio.seek(-1, 1)

            rs = pandas.read_csv(sio, encoding="GBK", index_col=0, parse_dates=True)
            #日期,股票代码,名称,收盘价,最高价,最低价,开盘价,前收盘,涨跌额,涨跌幅,成交量,成交金额
            h = rs[[u"开盘价", u"最高价", u"最低价", u"收盘价", u"成交量", u"收盘价"]].copy()
            h.columns = Market.HISTORY_COLUMNS

            if self._get_symbol_type(symbol) == "stock":
                split_history = self.get_split_history(symbol)
                if split_history: self.adjust_close_price(h, split_history)

            h.sort(ascending=True, inplace=True) # expect data to be ascending

            return h
        except HTTPError, e:
            _env.logger.debug("retrieve_history(): '%s' error:\n%s", url, e)

    #---------------------------------------------------------------------------
    QUOTE_TODAY_URL = "http://api.money.126.net/data/feed/%s,money.api"
    def get_quote_today(self, symbol):
        code = self._code7(symbol)
        url = self.QUOTE_TODAY_URL % code
        _env.logger.debug("get_quote_today(): '%s'", url)
        try:
            response = urlopen(url)
            data = response.read()
            start, end = data.find("(") + 1, data.find(")")
            data = data[start:end]
            data = json.loads(data)[code]
            rs = { "Open"      : data["open"],
                     "High"      : data["high"],
                     "Low"       : data["low"],
                     "Close"     : data["yestclose"] + data["updown"],
                     # 历史数据: 指数(手), 普通股票(股)
                     "Volume"    : data["volume"] if self._get_symbol_type(symbol) == "stock" else data["volume"] / 100,
                     "Adj Close" : data["yestclose"] + data["updown"],
                    }
            _env.logger.info("get_quote_today(): %s => price: %.2f, updown: %.2f, %.2f%%",
		             symbol, rs["Close"], data["updown"], data["updown"]*100/data["yestclose"])
	    return rs
        except HTTPError, e:
            _env.logger.debug("open '%s' result error.\n%s", url, e)


#===============================================================================
TradeHour = namedtuple('TradeHour', ['open', 'close'])
TradeTime = namedtuple("TradeTime", ["hour", "minute"])

class Market(object):
    name_cache = shelve.open("name.cache")
    HISTORY_COLUMNS = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]

    #---------------------------------------------------------------------------
    def _trading_day(self, dt=None):
        if not dt: dt = self.now.date()
        return False if dt.weekday() in (5, 6) or dt in self.holidays else True

    #---------------------------------------------------------------------------
    @property
    def now(self):
        return _env.now.astimezone(self.tz)

    @property
    def today(self):
        return self.now.date()

    @property
    def _today(self):
        return self.today.strftime("%Y-%m-%d")

    @property
    def last_trading_day(self):
        if self.now.hour < self.trading_hour.open.hour:
            dt = self.today - timedelta(1)
        else:
            dt = self.today
        while not self._trading_day(dt):
            dt -= timedelta(1)

        return dt

    def closed(self):
        if not self._trading_day():
            return True

        if self.trading_hour.open <= (self.now.hour, self.now.minute) <= self.trading_hour.close:
            return False

        return True

    def retrieve_history(self, symbol, _start, _end=_env._today, normalize=True):
        start, end = datetime.strptime(_start, "%Y-%m-%d").date(), datetime.strptime(_end, "%Y-%m-%d").date()
        while not self._trading_day(start):
            start += timedelta(1)
        if _end == _env._today:
            end = self.today
            _end = self._today

        cache = join("cache", "%s.hd5" % symbol)
        refresh, patch_today = True, False

        # no today's data is ok before market close
        if end == self.today and not self.closed():
            end = self.last_trading_day
            patch_today = True

        if end > self.last_trading_day:
            end = self.last_trading_day

        if exists(cache):
            store = HDFStore(cache)
            hd = store.get("history_daily")
            if start >= hd.index[0].date() and end <= hd.index[-1].date():
                # http://stackoverflow.com/questions/16175874/python-pandas-dataframe-slicing-by-date-conditions
                istart = hd.index.searchsorted(start)
                iend = hd.index.searchsorted(end) + 1
                refresh = False
                hd = hd.ix[istart:iend]

        if refresh:
            hd = self.datasource.retrieve_history(symbol, _start, _end)
            # patch head
            if hd.index[0].date() > start:
                df = pandas.DataFrame(index=pandas.DatetimeIndex(start=start, end=start, freq="D"),
                                      columns=Market.HISTORY_COLUMNS, dtype=float)
                df.ix[0] = hd.ix[0]
                hd = df.append(hd)
                #print hd.head()
            store = HDFStore(cache)
            store.put("history_daily", hd)
            store.flush()

        if patch_today:
            df = pandas.DataFrame(index=pandas.DatetimeIndex(start=self.today, end=self.today, freq="D"),
                                  columns=Market.HISTORY_COLUMNS, dtype=float)
            row_today = self.datasource.get_quote_today(symbol)
            if row_today:
                df.ix[0] = pandas.Series(row_today)
                # http://stackoverflow.com/questions/15891038/pandas-change-data-type-of-columns
                df["Volume"] = df["Volume"].astype(int)
                hd = hd.append(df)

        if normalize:
            # http://luminouslogic.com/how-to-normalize-historical-data-for-splits-dividends-etc.htm
            hd["_Open"] = hd["Open"] * hd["Adj Close"] / hd["Close"]
            hd["_High"] = hd["High"] * hd["Adj Close"] / hd["Close"]
            hd["_Low"] = hd["Low"] * hd["Adj Close"] / hd["Close"]
            hd["_Close"] = hd["Adj Close"]
            #print hd.tail(30)

            del hd["Open"], hd["High"], hd["Low"], hd["Close"], hd["Adj Close"]
            hd.rename(columns=lambda c: c.replace('_', ''), inplace=True)

            return hd

    def get_symbol_name(self, symbol):
        name = self.name_cache.get(symbol)
        if not name:
            name = self.datasource.get_symbol_name(symbol)
            self.name_cache[symbol] = name
            self.name_cache.sync()

        return name

#===============================================================================
@singleton
class NasdaQ(Market):
    tz = timezone("America/New_York")

    # http://www.nasdaq.com/about/trading-schedule.aspx
    #trading_hour = TradeHour(TradeTime(9, 30), TradeTime(16, 0))
    # force to retrieve today's price
    trading_hour = TradeHour(TradeTime(9, 30), TradeTime(21, 0))

    # http://en.wikipedia.org/wiki/Public_holidays_in_the_United_States
    year = _env.now.year
    holidays = [ date(year, 1, 1), # New Year's Day
                 (datetime(year, 1, 1) + relativedelta(weekday=MO(3))).date(), # Martin Luther King, Jr.
                 (datetime(year, 2, 1) + relativedelta(weekday=MO(3))).date(), # Presidents' Day
                 (datetime(year, 6, 1) + relativedelta(weekday=MO(-1))).date(), # Memorial Day
                 date(year, 7, 4), # Independence Day
                 (datetime(year, 9, 1) + relativedelta(weekday=MO(1))).date(), # Labor Day
                 (datetime(year, 10, 1) + relativedelta(weekday=MO(2))).date(), # Columbus Day
                 date(year, 11, 11), # Veterans Day
                 (datetime(year, 11, 1) + relativedelta(weekday=TH(4))).date(), # Thanksgiving Day
                 date(year, 12, 25), # Christmas
               ]

    def __init__(self):
        self.datasource = Yahoo()

#===============================================================================
@singleton
class ChinaA(Market):
    tz = timezone("Asia/Shanghai")

    # www.sse.com.cn/marketservices/investors/home/trading/c/51544.shtml
    #trading_hour = TradeHour(TradeTime(9, 30), TradeTime(15, 0))
    # force to retrieve today's price
    trading_hour = TradeHour(TradeTime(9, 30), TradeTime(18, 0))

    #http://en.wikipedia.org/wiki/Public_holidays_in_China
    holidays = [ date(2014, 1, 1),  # New 2014's Day
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
               ]

    def __init__(self):
        self.datasource = NetEase()

#===============================================================================
class PivotCalculator(object):
    #---------------------------------------------------------------------------
    @classmethod
    def find_extrim(klass, l, wl, wr, _op=operator.ge):
            ti = i = wl
            while i < wr:
                if _op(l[i], l[ti]): ti = i
                i += 1

            return ti

    @classmethod
    def find_pivots(klass, l, look_around=4, _op=operator.ge):
        pivots = []
        # initialize the tentative pivot
        ti = klass.find_extrim(l, 0, look_around + 1, _op)
        time_to_break = False
        while True:
            # verifiy the tentative pivot
            # look back
            wl = max(ti - look_around + 1, 0)
            # look forward
            wr = min(ti + look_around + 1, len(l))
            _ti = klass.find_extrim(l, wl, wr, _op)

            #print "ti, _ti = %d, %d" % (ti, _ti)
            if _ti == ti:
                pivots.append(ti)
                wl = min(ti + look_around + 1, len(l))
            else:
                wl = min(ti + 1, len(l))

            if time_to_break: break

            # find the new tentative pivot
            wr = min(wl + look_around + 1, len(l))
            ti = klass.find_extrim(l, wl , wr, _op)

            if wr == len(l): time_to_break = True

        return pivots

    @classmethod
    def merged_pivots(klass, l, tops, btms, minimum_distance=5):
        pivots, ti, bi = [], 0, 0
        while ti < len(tops) or bi < len(btms):
            if bi >= len(btms) or (ti < len(tops) and tops[ti] < btms[bi]):
                pivots.append(("H", tops[ti], l[tops[ti]]))
                ti += 1
            elif ti >= len(tops) or (bi < len(btms) and btms[bi] < tops[ti]):
                pivots.append(("L", btms[bi], l[btms[bi]]))
                bi += 1

            _pivots, i = [], 0
            while i < len(pivots):
                target = None
                while i < len(pivots) and pivots[i][0] == "H":
                    if not target or target[2] <= pivots[i][2]:
                        target = pivots[i]
                    i += 1
                if target: _pivots.append(target)

                target = None
                while i < len(pivots) and pivots[i][0] == "L":
                    if not target or target[2] >= pivots[i][2]:
                        target = pivots[i]
                    i+= 1
                if target: _pivots.append(target)

        return _pivots


    #---------------------------------------------------------------------------
    def __call__(self, l, look_around=5):
        assert isinstance(l, list), "l must be a list!"
        highs = self.find_pivots(l, look_around=look_around, _op=operator.ge)
        lows = self.find_pivots(l, look_around=look_around, _op=operator.le)
        pivots = self.merged_pivots(l, highs, lows)

        return highs, lows, pivots


#===============================================================================
class ATRCalculator(object):
    def __init__(self, atr_period):
        self.atr_period = atr_period
        self.tr_list = []
        self.last_tick = None
        self.atr = None

    def __call__(self, tick):
        HL = tick["High"] - tick["Low"]
        # if not self.last_tick:
        # => ValueError: 'The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()'
        if self.last_tick is not None:
            HCp = abs(tick["High"] - self.last_tick["Close"])
            LCp = abs(tick["Low"] - self.last_tick["Close"])
            tr = max(HL, HCp, LCp)
        else:
            tr = HL
        self.last_tick = tick.copy()

        assert tr != 0.0, "TR should not be zero!"
        if len(self.tr_list) < self.atr_period:
            self.tr_list.append(tr)
            self.atr = sum(self.tr_list) / len(self.tr_list)
        else:
            #self.atr = (self.atr * (atr_period - 1) + self.tr) / atr_period
            self.atr += (tr - self.atr) / self.atr_period

        return self.atr

#===============================================================================
# ODR => One Day Reversal
class ODRCalculator(object):
    def __init__(self, price_threshhold=.01, volume_threshhold=0.1):
        self.price_threshhold = price_threshhold
        self.volume_threshhold = volume_threshhold
        self.last_tick = None

    def __call__(self, tick):
        result = False
        if not self.last_tick is None:
            if (tick["High"] > self.last_tick["High"]
                and tick["Close"] < self.last_tick["Low"]
                and tick["Volume"] > self.last_tick["Volume"]
                ):
                _env.logger.debug("ODR: %s", tick.name)
                result = True

        self.last_tick = tick.copy()

        return result

#===============================================================================
# cannot be redefined to other value
BAND_UPWARD     = 6
BAND_NAT_RALLY  = 5
BAND_SEC_RALLY  = 4
BAND_SEC_REACT  = 3
BAND_NAT_REACT  = 2
BAND_DNWARD     = 1
BAND_UNKNOWN    = 0

class LMKBandCalculator(object):
    def __init__(self, atr_factor=1.0):
        self.atr_factor = atr_factor * 2.0
        self.rsst = 0.0
        self.sppt = 0.0
        self.prv_pivot = ""
        self.prv_band = BAND_UNKNOWN
        self.water_mark = 0.0

    def __call__(self, tick):
        def normalize_band(band):
            if band > BAND_UPWARD: band = BAND_UPWARD
            if band < BAND_DNWARD: band = BAND_DNWARD
            return band

        assert tick["ATR"] != 0, "ATR should not be zero."
        band_width = tick["ATR"] * self.atr_factor
        _close = tick["Close"]
        band = BAND_UNKNOWN

        if "H" in tick["Pivot"]:
            self.rsst = _close
            self.water_mark = self.rsst
            self.prv_pivot = "H"
            self.prv_band = BAND_UPWARD

        elif "L" in tick["Pivot"]:
            self.sppt = _close
            self.warter_mark = self.sppt
            self.prv_pivot = "L"
            self.prv_band = BAND_DNWARD

        # trending downward ...
        if self.prv_pivot == "H":
            band = 6 - int(math.floor((self.rsst - _close) / (band_width / 6.0)))
            band = normalize_band(band)

        # trending upward ...
        if self.prv_pivot == "L":
            band = int(math.ceil((_close - self.sppt) / (band_width / 6.0)))
            band = normalize_band(band)

        if band != self.prv_band:
            self.water_mark = _close
        else:
            if band >= BAND_SEC_RALLY:
                if _close > self.water_mark:
                    self.water_mark = _close
                    if band == BAND_UPWARD:
                        self.rsst = self.water_mark

            if band <= BAND_SEC_REACT:
                if _close < self.water_mark:
                    self.water_mark = _close
                    if band == BAND_DNWARD:
                        self.sppt = self.water_mark

        self.prv_band = band
        return pandas.Series({ "WM": self.water_mark, "BAND": band })

#===============================================================================
class EntryExitCalculator(object):
    def __init__(self, atr_factor=1.0):
        self.atr_factor = atr_factor
        self.trade = "-"
        self.pivot = ("", 0)
        self.stock = self.prv_stock = 0
        self.cost = 0

    def __call__(self, tick):
        atr = tick["ATR"] * self.atr_factor
        pivot_type, pivot_price = self.pivot
        if tick["WM"] == tick["Close"]:
            if tick["BAND"] == BAND_DNWARD:
                if pivot_type != "L" or (pivot_type == "L" and tick["Close"] < pivot_price):
                    pivot_price = tick["Close"]
                    self.pivot = ("L", pivot_price)
            elif tick["BAND"] == BAND_UPWARD:
                if pivot_type != "H" or (pivot_type == "H" and tick["Close"] > pivot_price):
                    pivot_price = tick["Close"]
                    self.pivot = ("H", pivot_price)

        pivot_type, pivot_price = self.pivot
        if pivot_type == "L":
            if tick["Close"] > pivot_price + atr/2:
                self.stock = 1
                self.cost = tick["Close"]
            elif self.stock == 1 and tick["Close"] <= self.cost - atr/2: # break low
                self.stock = 0
                self.cost = tick["Close"]
        elif pivot_type == "H":
            if tick["Close"] <= pivot_price - atr/2:
                self.stock = 0
                self.cost = tick["Close"]
            elif self.stock == 0 and tick["Close"] > self.cost + atr/2: # break high
                self.stock = 1
                self.cost = tick["Close"]

        self.trade = "-"
        if self.stock == 1 and self.prv_stock == 0:
            self.trade = "B"
        if self.stock == 0 and self.prv_stock == 1:
            self.trade = "S"

        self.prv_stock = self.stock

        return self.trade

#===============================================================================
#### main() ####
#===============================================================================
class Stock(object):
    def __init__(self, symbol):
        self.symbol = symbol
        self.market = ChinaA() if symbol[-3:] in (".SS", ".SZ") else NasdaQ()

    @property
    def name(self):
        return self.market.get_symbol_name(self.symbol)

    def retrieve_history(self, _start, _end):
        self.history = self.market.retrieve_history(self.symbol, _start, _end)
        return self.history

    def process_history(self, freq="D", pivot_look_around=5):
        h = self.history

        # without .copy(), you will get SettingWithCopyWarning somewhere ...
        h = h[h["Volume"] != 0].copy()

        c = ATRCalculator(atr_period=20)
        h["ATR"] = h.apply(c, axis=1)
        h.fillna(method="backfill", axis=0, inplace=True)

        if freq != "D":
            resampled = pandas.DataFrame(h["Close"].resample(freq, how="last"), columns=("Close",))
            resampled["Open"] = h["Open"].resample(freq, how="first")
            resampled["High"] = h["High"].resample(freq, how="max")
            resampled["Low"] = h["Low"].resample(freq, how="min")
            resampled["Volume"] = h["Volume"].resample(freq, how="sum")
            assert "ATR" in h.columns, "ATR needs to be processed in daily data!"
            resampled["ATR"] = h["ATR"].resample(freq, how="last")

            self.history = resampled
            h = self.history

        # e.g. the spring festival week
        dropped = h.dropna(axis=0, inplace=True)
        if dropped is not None:
            _env.logger.debug("NA dropped: %s" % dropped)

        c = ODRCalculator()
        h["ODR"] = h.apply(c, axis=1)

        # necessary to calculate updown
        h["CC"] = h["Close"].pct_change()
        h.fillna(method="backfill", axis=0, inplace=True)

        # Pivot points, necessary to calculate band
        pc = PivotCalculator()
        closes = list(h["Close"])
        highs, lows, pivots = pc(closes, look_around=pivot_look_around)
        h["Pivot"] = ""
        _pivots = [p[1] for p in pivots]
        h.ix[_pivots, "Pivot"] += "P"
        h.ix[highs, "Pivot"] += "H"
        h.ix[lows, "Pivot"] += "L"

        c = LMKBandCalculator(atr_factor=1.0)
        band_watermark = h.apply(c, axis=1)
        h = pandas.merge(h, band_watermark, left_index=True, right_index=True, sort=False)

        c = EntryExitCalculator(atr_factor=1.0)
        h["EE"] = h.apply(c, axis=1)

        self.history = h

    def visualize(self, components="C,CL,HLC,BAND,BANDL,WM,PV,PVL,ODR,EE", fluct_factor=.5):
        components = re.split("[-:,;.]", components)
        h = self.history

        #-----------------------------------------------------------------------
        ax0 = plt.subplot2grid((5,1), (0, 0), rowspan=4)
        ax0.set_xmargin(0.02)
        ax1 = plt.subplot2grid((5,1), (4, 0), rowspan=1, sharex=ax0)
        ax1.yaxis.set_visible(False)
        figure = plt.gcf()
        #figure.suptitle(self.name)
        figure.subplots_adjust(hspace=0)

        min_close = min(h["Close"])
        max_close = max(h["Close"])
        height = min_close * fluct_factor
        ymin =  min_close * 0.98
        ymax = min_close + (height * 1.02)
        if ymax < max_close:
            height = max_close - min_close
            ymax = min_close + height * 1.02
        ax0.set_ylim(ymin, ymax)

        ax0.set_axis_bgcolor('white')
        ax1.set_axis_bgcolor('white')

        #-----------------------------------------------------------------------
        # Basic price line
        if "CL" in components:
            ax0.plot(h.index, h["Close"], "-", color="black", alpha=0.5)

        # Water Mark
        if "WM" in components:
            r = h.query("WM > 0")
            ax0.plot(r.index, r["WM"], "c-", drawstyle="steps-post", alpha=1.0)

        # Pivots, major Trend
        # XXX: https://github.com/pydata/pandas/issues/6155
        pivots = h.query("Pivot == 'PH' or Pivot == 'PL'")
        if "PVL" in components:
            ax0.plot(pivots.index, pivots["Close"], "-", color="blue", alpha=.3)
            rs = h.query("Pivot == 'PH' or Pivot == 'H'")
            ax0.plot(rs.index, rs["Close"], "g^", alpha=1.0)
            rs = h.query("Pivot == 'PL' or Pivot == 'L'")
            ax0.plot(rs.index, rs["Close"], "rv", alpha=1.0)

        if "PV" in components:
            for i in range(len(pivots)):
                x = pivots.index[i]
                if "H" in pivots.ix[i]["Pivot"]:
                    y = pivots.ix[i]["High"]
                else: #if "L" in pivot["Pivot"]:
                    y = pivots.ix[i]["Low"]
                s = "%.2f" % pivots.ix[i]["Close"]
                ax0.text(x, y, s, alpha=.5)

        # Basic HLC/Volume Chart
        # Ups ...
        rs = h.query("CC >= 0")
        # Volume
        ax1.bar(rs.index, rs["Volume"], width=1, color="black", edgecolor="black", linewidth=1, alpha=.3, align="center")
        if "C" in components:
            ax0.plot(rs.index, rs["Close"], "_", color="black", alpha=.5, markeredgewidth=2)
        if "HLC" in components:
            ax0.plot(rs.index, rs["Close"], "_", color="black", alpha=1, markeredgewidth=1)
	    rs = h.query("Close >= Open")
            ax0.vlines(rs.index, rs["Low"], rs["High"], color="black", edgecolor="black", alpha=1, linewidth=1)

        # Downs ...
        rs = h.query("CC < 0")
        # Volume
        ax1.bar(rs.index, rs["Volume"], width=1, color="red", edgecolor="red", linewidth=1, alpha=.3, align="center")
        if "C" in components:
            ax0.plot(rs.index, rs["Close"], "_", color="red", alpha=.5, markeredgewidth=2)
        if "HLC" in components:
            ax0.plot(rs.index, rs["Close"], "_", color="red", alpha=1, markeredgewidth=1)
	    rs = h.query("Close < Open")
            ax0.vlines(rs.index, rs["Low"], rs["High"], color="red", alpha=1, linewidth=1)

        if "BAND" in components:
            style_dict = {
                BAND_DNWARD     : "rv",
                BAND_NAT_REACT  : "m<",
                BAND_SEC_REACT  : "m*",
                BAND_SEC_RALLY  : "c*",
                BAND_NAT_RALLY  : "c>",
                BAND_UPWARD     : "g^",
            }
            for band in range(BAND_DNWARD, BAND_UPWARD + 1):
                #if band in (BAND_SEC_REACT, BAND_SEC_RALLY): continue
                rs = h.query("WM == Close and BAND == %s" % band)
                ax0.plot(rs.index, rs["Close"], style_dict[band], alpha=1.0)

        if "BANDL" in components:
            # up trend
            mask = ma.make_mask(h.index)
            mask = ma.masked_where(((h["BAND"] >= BAND_NAT_REACT) | (h["EE"] == "B")) & (h["EE"] != "S"), mask)
            chosen = ma.masked_where(~mask.mask, h["Close"])
            if chosen.any():
                ax0.plot(h.index, chosen, "g-", linewidth=1, alpha=1)
            # down trend
            mask = ma.make_mask(h.index)
            mask = ma.masked_where(((h["BAND"] <= BAND_NAT_REACT) | (h["EE"] == "S")) & (h["EE"] != "B"), mask)
            chosen = ma.masked_where(~mask.mask, h["Close"])
            if chosen.any():
                ax0.plot(h.index, chosen, "r-", linewidth=1, alpha=.5)

        # ODR => One Day Reversal
        if "ODR" in components:
            rs = h.query("ODR == True")
            ax0.plot(rs.index, rs["Close"], "rx", markersize=8, markeredgewidth=3, alpha=1)

        # Entry/Exit Points
        if "EE" in components:
            rs = h.query("EE =='B'")
            ax0.plot(rs.index, rs["Close"], "g+", markersize=8, markeredgewidth=3, alpha=1)
            rs = h.query("EE =='S'")
            ax0.plot(rs.index, rs["Close"], "r_", markersize=8, markeredgewidth=3, alpha=1)

        #-----------------------------------------------------------------------
        days = WeekdayLocator(MONDAY)
        #days = WeekdayLocator(FRIDAY)
        #dayFmt = DateFormatter("%d")
        def _dayFmt(x, pos):
            dt = pylab.num2date(x)
            return dt.strftime("%d")[-1] if dt.day < 10 else dt.strftime("%d")
        dayFmt = FuncFormatter(_dayFmt)

        months  = MonthLocator(range(1, 13), bymonthday=1, interval=1)
        # http://stackoverflow.com/questions/11623498/date-formatting-with-matplotlib
        def _monthFmt(x, pos):
            dt = pylab.num2date(x)
            return dt.strftime('\n%Y') if dt.month == 1 else dt.strftime("\n%b")
        monthFmt = FuncFormatter(_monthFmt)

        for ax in (ax0, ax1):
            ax.xaxis.set_major_locator(months)
            ax.xaxis.set_major_formatter(monthFmt)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color="blue")
            if len(ax.get_xticks()) <= 12:
                ax.xaxis.set_minor_locator(days)
                ax.xaxis.set_minor_formatter(dayFmt)

        ax0.xaxis.grid(True, which='major', color="blue", linestyle="-", alpha=1)
        ax0.xaxis.grid(True, which='minor', color="gray", linestyle="-", alpha=.5)
        ax0.tick_params(labelbottom="off", which="both")
        ax0.yaxis.grid(True)

        ax1.xaxis.grid(True, which='major', color="blue", linestyle="-", alpha=1)
        ax1.xaxis.grid(True, which='minor', color="gray", linestyle="-", alpha=.3)

        # http://stackoverflow.com/questions/12750355/python-matplotlib-figure-title-overlaps-axes-label-when-using-twiny
        ax0.set_title("%s%s" % (self.symbol, "" if self.symbol == self.name else ("(%s)" % self.name)), y=0.9)

        plt.show()

