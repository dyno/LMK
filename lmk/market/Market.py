from time import strftime
from os.path import join, exists
from datetime import date, datetime, timedelta
from collections import namedtuple

from pandas import Series, Timestamp, to_datetime

from ..utils import env
from ..cache import Cache


TradeHour = namedtuple('TradeHour', ['open', 'close'])
TradeTime = namedtuple("TradeTime", ["hour", "minute"])

class Market:
    HISTORY_COLUMNS = ["Open", "High", "Low", "Close", "Volume", "Adj Close"]

    tz = None
    def __init__(self):
        self._now = None
        self.cache = Cache()

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
        self._now = to_datetime(dt) if dt else None
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

    def retrieve_history(self, symbol, _start, _end=env._today, normalize=True, patch_today=True):
        start, end = to_datetime(_start).date(), to_datetime(_end).date()
        h = self.cache.get(symbol, start, end)
        if h is None:
            do_patch_today = False
            if end == self.today and self._trading_day():
                do_patch_today = patch_today
                # XXX: No today's data before market close. Even after the market close,
                # the data might take some time to appear. We should not expect cache to have it.
                end = self.today - timedelta(1)
                h = self.cache.get(symbol, start, end)

            if h is None:
                h = self.datasource.retrieve_history(symbol, _start, _end)
                if self.today in h.index:
                    end = self.today
                self.cache.put(symbol, start, end, h)

            if do_patch_today and self.today not in h.index:
                r = self.datasource.get_quote_today(symbol)
                if r:
                    h.loc[Timestamp(self._today)] = Series(r)

        assert h is not None

        if normalize:
            # http://luminouslogic.com/how-to-normalize-historical-data-for-splits-dividends-etc.htm
            h["_Open"] = h["Open"] * h["Adj Close"] / h["Close"]
            h["_High"] = h["High"] * h["Adj Close"] / h["Close"]
            h["_Low"] = h["Low"] * h["Adj Close"] / h["Close"]
            h["_Close"] = h["Adj Close"]

            del h["Open"], h["High"], h["Low"], h["Close"], h["Adj Close"]
            h.rename(columns=lambda c: c.replace('_', ''), inplace=True)

            return h

    def get_symbol_name(self, symbol):
        if symbol in self.cache.name.index:
            name = self.cache.name.loc[symbol]
        else:
            name = self.datasource.get_symbol_name(symbol)
            self.cache.name.loc[symbol] = name
            self.cache.flush_name()

        return name

    def set_datasource(self, ds):
        self.datasource = self.datasources[ds]

