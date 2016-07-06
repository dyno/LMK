from time import strftime
from os.path import join, exists
from datetime import date, datetime, timedelta
from collections import namedtuple

from pandas import Series, DataFrame, DatetimeIndex, HDFStore, to_datetime

from ..utils import env
from ..config import CACHE_DIR


TradeHour = namedtuple('TradeHour', ['open', 'close'])
TradeTime = namedtuple("TradeTime", ["hour", "minute"])

class Market(object):
    HISTORY_COLUMNS = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]

    def __init__(self):
        self._now = None
        self.tz = None

    def _trading_day(self, dt=None):
        if not dt:
            dt = self.now.date()
        # neither weekends nor holidays
        return dt.weekday() not in (5, 6) and dt not in self.holidays

    @property
    def now(self):
        return self._now if self._now else datetime.now(tz=self.tz)

    @now.setter
    def now(self, dt=None):
        self._now = to_datetime(dt).to_datetime() if dt else None
        if self._now:
            self._now.replace(tzinfo=self.tz)

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

    @property
    def open(self):
        hour, minute = self.now.hour, self.now.minute

        return self._trading_day() and \
            self.trading_hour.open <= (hour, minute) <= self.trading_hour.close

    @property
    def closed(self):
        return not self.open

    def retrieve_history(self, symbol, _start, _end=env._today, normalize=True):
        start = to_datetime(_start).date()
        end = to_datetime(_end).date()
        while not self._trading_day(start):
            start += timedelta(1)
        if _end == env._today:
            end = self.today
            _end = self._today

        cache = join(CACHE_DIR, "%s.hd5" % symbol)
        refresh, patch_today = True, False

        # no today's data is ok before market close
        if end == self.today and not self.closed:
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
                df = DataFrame(index=DatetimeIndex(start=start, end=start, freq="D"),
                               columns=Market.HISTORY_COLUMNS, dtype=float)
                df.ix[0] = hd.ix[0]
                hd = df.append(hd)
                #print hd.head()
            store = HDFStore(cache)
            store.put("history_daily", hd)
            store.flush()

        if patch_today:
            df = DataFrame(index=DatetimeIndex(start=self.today, end=self.today, freq="D"),
                                  columns=Market.HISTORY_COLUMNS, dtype=float)
            row_today = self.datasource.get_quote_today(symbol)
            if row_today:
                df.ix[0] = Series(row_today)
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

        return name

    def set_datasource(self, ds):
        self.datasource = self.datasources[ds]

