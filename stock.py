#!/usr/bin/env python

import sys
from os.path import exists, join
from datetime import date

import pandas
from pandas.io.data import DataReader
from pandas import HDFStore, Series, DataFrame

import log

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
            self.store = HDFStore(store_name)
            self.store.put("history", self.history_daily)
            if not no_volume: # index like 000001.SS has no volume data
                # suspension - no trading event
                self.history_daily = self.history_daily[self.history_daily["Volume"] != 0]
            self.store.flush()

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


