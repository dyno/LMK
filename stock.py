#!/usr/bin/env python

import urllib2
import sys
import csv
from os.path import exists, join
from datetime import date

import pandas
from pandas.io.data import DataReader
from pandas import HDFStore, Series, DataFrame

import log

# http://www.gummy-stuff.org/Yahoo-data.htm
YAHOO_TODAY="http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=sd1ohgl1vl1"

def get_quote_today(symbol):
    response = urllib2.urlopen(YAHOO_TODAY % symbol)
    reader = csv.reader(response, delimiter=",", quotechar='"')
    for row in reader:
        if row[0] == symbol and row[1] != "N/A":
            return row

#--------------------------------------------------------------------------------
class Stock(object):
    def __init__(self, name):
        self.name = name
        self.freq = "D"

    def retrieve_history(self, use_cache=True, start="12/1/2013", end=date.today(), no_volume=False):
        store_name = join("cache", "%s.hd5" % self.name)

        if use_cache and exists(store_name):
            self.store = HDFStore(store_name)
            self.history_daily = self.store.get("history")
        else:
            self.history_daily = DataReader(self.name, "yahoo", start, end)
            #self.history_daily = DataReader(self.name, "google", start, end)
            # append today's data
            last = pandas.to_datetime(self.history_daily.ix[-1].name).date()
            today = date.today()
            if pandas.to_datetime(end).date() == today and last != today:
                row = get_quote_today(self.name)
                if row:
                    df = pandas.DataFrame(index=pandas.DatetimeIndex(start=today, end=today, freq="D"),
                                          columns=["Open", "High", "Low", "Close", "Volume", "Adj Close"], dtype=float)
                    df.ix[0] = map(float, row[2:])
                    # http://stackoverflow.com/questions/15891038/pandas-change-data-type-of-columns
                    df["Volume"] = df["Volume"].astype(int)
                    self.history_daily = self.history_daily.append(df)

            self.store = HDFStore(store_name)
            self.store.put("history", self.history_daily)
            self.store.flush()

        if not no_volume: # index like 000001.SS has no volume data
            # suspension - no trading event
            self.history_daily = self.history_daily[self.history_daily["Volume"] != 0]

        self.history = self.history_daily

    def resample_history(self, freq="W-FRI"):
        # http://pandas.pydata.org/pandas-docs/dev/timeseries.html#offset-aliases
        self.freq = freq
        if freq == "D":
            self.history = self.history_daily
            return

        history_resampled = DataFrame(self.history_daily["Close"].resample(freq, how="last"), columns=("Close",))
        history_resampled["Open"] = self.history_daily["Open"].resample(freq, how="first")
        history_resampled["High"] = self.history_daily["High"].resample(freq, how="max")
        history_resampled["Low"] = self.history_daily["Low"].resample(freq, how="min")
        history_resampled["ATR"] = self.history_daily["ATR"].resample(freq, how="last")
        # e.g. the spring festival week
        #self.history_resampled.fillna(method="ffill", inplace=True)
        dropped = history_resampled.dropna(axis=0, inplace=True)
        if dropped is not None:
            log.logger.debug("NA droped: %s" % dropped)

        self.history = history_resampled

if __name__ == "__main__":
    print get_quote_today("YOKU")
    stk = Stock("YOKU")
    stk.retrieve_history(start="1/1/2013", use_cache=False)
    print stk.history_daily.tail()
