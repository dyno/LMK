#!/usr/bin/env python

import sys
from os.path import exists, join
from datetime import date, timedelta

import pandas
from pandas import HDFStore, DataFrame

import log
from MyDataReader import MyDataReader
from ATRCalculator import ATRCalculator
from ODRCalculator import ODRCalculator

#--------------------------------------------------------------------------------
class Stock(object):
    def __init__(self, symbol):
        self.symbol = symbol
        # http://quotes.money.163.com/stocksearch/json.do?count=1&word=300052
        self.name = symbol
        self.freq = "D"

    def retrieve_history(self, start="12/1/2013", end=date.today(), use_cache=True,
                         no_volume=False, atr_period=20):
        store_name = join("cache", "%s.hd5" % self.symbol)

        if use_cache and exists(store_name):
            self.store = HDFStore(store_name)
            self.history_daily = self.store.get("history")
        else:
            self.history_daily = MyDataReader(self.symbol, start, end)
            self.store = HDFStore(store_name)
            self.store.put("history", self.history_daily)
            self.store.flush()

        # just make sure the data is sorted ascending
        self.history_daily.sort(ascending=True, inplace=True)

        if not no_volume: # index like 000001.SS has no volume data
            # suspension - no trading event
            self.history_daily = self.history_daily[self.history_daily["Volume"] != 0]

        # process ATR
        c = ATRCalculator(atr_period=20)
        self.history_daily["ATR"] = self.history_daily.apply(c, axis=1)
        self.history_daily.fillna(method="backfill", axis=0, inplace=True)

        c = ODRCalculator(price_threshhold=.01)
        self.history_daily["ODR"] = self.history_daily.apply(c, axis=1)

        # slice data between requested period, history has to be sorted
        # http://stackoverflow.com/questions/16175874/python-pandas-dataframe-slicing-by-date-conditions
        start = pandas.to_datetime(start)
        end = pandas.to_datetime(end) + timedelta(days=1)
        self.history = self.history_daily[start:end]

    def resample_history(self, freq="W-FRI"):
        # http://pandas.pydata.org/pandas-docs/dev/timeseries.html#offset-aliases
        self.freq = freq
        if freq == "D": return

        history_resampled = DataFrame(self.history["Close"].resample(freq, how="last"), columns=("Close",))
        history_resampled["Open"] = self.history["Open"].resample(freq, how="first")
        history_resampled["High"] = self.history["High"].resample(freq, how="max")
        history_resampled["Low"] = self.history["Low"].resample(freq, how="min")
        history_resampled["Volume"] = self.history["Volume"].resample(freq, how="sum")
        assert "ATR" in self.history.columns, "ATR needs to be processed in daily data!"
        history_resampled["ATR"] = self.history["ATR"].resample(freq, how="last")
        c = ODRCalculator(threshhold=.01)
        history_resampled["ODR"] = history_resampled.apply(c, axis=1)

        # e.g. the spring festival week
        #self.history_resampled.fillna(method="ffill", inplace=True)
        dropped = history_resampled.dropna(axis=0, inplace=True)
        if dropped is not None:
            log.logger.debug("NA droped: %s" % dropped)

        self.history = history_resampled


    def process_atr(self, atr_period=20):
        history = stk.history

if __name__ == "__main__":
    from common import probe_proxy
    probe_proxy()
    log.init()

    #for symbol in ("YOKU", "399006.SZ", "000001.SS"):
    for symbol in ("YOKU", "NTES"):
        stk = Stock(symbol)
        stk.retrieve_history(start="1/1/2013", use_cache=False, no_volume=True)
        print symbol
        print stk.history.head()
        print stk.history.tail()

