#!/usr/bin/env python

import traceback
import sys
import math
import logging
from os.path import exists, join
from datetime import date

import matplotlib.pyplot as plt
import pandas
from pandas.io.data import DataReader
from pandas import HDFStore, Series, DataFrame
from numpy import ma
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY, FRIDAY
import matplotlib.ticker as ticker

from atr import ATRCalculator as ATRC
from lmk import LivermoreMarketKeyCalculator as LMKC, LivermoreMaketKeyBacktestCalculator as LMKBC
from lmk import BAND_DOWNWARD, BAND_NATURAL_REACT, BAND_SECOND_REACT, BAND_SECOND_RALLY, BAND_NATURAL_RALLY, BAND_UPWARD
from lmk import TREND_DOWNWARD, TREND_UPWARD

import log

#--------------------------------------------------------------------------------
class Stock(object):
    def __init__(self, name):
        self.name = name
        self.freq = "D"

    def retrieve_history(self, use_cache=True, start="12/1/2013", end=date.today()):
        store_name = join("cache", "%s.hd5" % self.name)

        if use_cache and exists(store_name):
            self.store = HDFStore(store_name)
            self.history_daily = self.store.get("history")
        else:
            self.history_daily = DataReader(self.name, "yahoo", start, end)
            #self.history_daily = DataReader(self.name, "google", start, end)
            self.store = HDFStore(store_name)
            self.store.put("history", self.history_daily)
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
        # e.g. the spring festival week
        #self.history_resampled.fillna(method="ffill", inplace=True)
        dropped = history_resampled.dropna(axis=0, inplace=True)
        if dropped is not None:
            log.logger.debug("NA droped: %s" % dropped)

        self.history = history_resampled

    def process_atr(self, atr_period=15):
        calculator = ATRC(atr_period)
        self.history["ATR"] = self.history.apply(calculator, axis=1)

    def process_livermore_market_key(self):
        calculator = LMKC()
        self.history = pandas.merge(self.history, self.history.apply(calculator, axis=1),
                                    left_index=True, right_index=True, sort=False)

    def process_backtest(self, fund=10000, commission=9.9):
        calculator = LMKBC(fund, commission)
        self.history["value"] = self.history.apply(calculator, axis=1)
        profit_rate = (calculator.value_rate() - 1) * 100
        log.logger.info("profit=%.2f%%", profit_rate)

        return profit_rate

    def plot_init(self):
        if hasattr(self, "ax") and not self.ax is None: return

        # http://matplotlib.org/examples/pylab_examples/color_by_yvalue.html
        #days = WeekdayLocator(MONDAY)
        days = WeekdayLocator(FRIDAY)
        months  = MonthLocator(range(1, 13), bymonthday=1, interval=1) # every month
        #monthsFmt = DateFormatter("%b '%y")
        #monthsFmt = DateFormatter("%b")
        monthsFmt = DateFormatter("%b")
        dayFmt = DateFormatter("%d")
        ax = plt.gca()
        ax.xaxis.set_major_locator(months)
        ax.xaxis.set_major_formatter(monthsFmt)
        ax.xaxis.set_minor_locator(days)
        ax.xaxis.set_minor_formatter(dayFmt)
        #ax.xaxis.set_minor_locator(ticker.MaxNLocator(10, prun="both"))
        ax.grid(True)
        ax.xaxis.grid(False, which='major')
        ax.xaxis.grid(True, which='minor')
        ax.set_xmargin(0.02)

        self.ax = ax

    def plot_livermore_trend(self, line="-", alpha=1, show_band=False, band_width=1):

        # http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.plot
        style_dict = {
            BAND_DOWNWARD       : "rv",
            BAND_NATURAL_REACT  : "m<",
            BAND_SECOND_REACT   : "m*",
            BAND_SECOND_RALLY   : "c*",
            BAND_NATURAL_RALLY  : "c>",
            BAND_UPWARD         : "g^",
        }

        close = self.history["Close"]
        atr = self.history["ATR"]
        level = self.history["level"]
        trend = self.history["trend"]
        resistance = self.history["resistance"]
        support = self.history["support"]

        for band in range(BAND_DOWNWARD, BAND_UPWARD + 1):
            mask = ma.make_mask(self.history.index)
            mask = ma.masked_where(level == band, mask)
            chosen = ma.masked_where(~mask.mask, close)
            if chosen.any():
                plt.plot(self.history.index, chosen, style_dict[band], alpha=alpha)

        # upward trend
        mask = ma.make_mask(self.history.index)
        #mask = ma.masked_where(level >= BAND_SECOND_RALLY, mask)
        mask = ma.masked_where(level >= BAND_SECOND_REACT, mask)
        chosen = ma.masked_where(~mask.mask, close)
        if chosen.any():
            plt.plot(self.history.index, chosen, "g%s" % line, alpha=alpha, label="^:%s" % self.freq.lower())

        # downward trend
        mask = ma.make_mask(self.history.index)
        mask = ma.masked_where(level <= BAND_SECOND_REACT, mask)
        chosen = ma.masked_where(~mask.mask, close)
        if chosen.any():
            plt.plot(self.history.index, chosen, "r%s" % line, alpha=alpha, label="v:%s" % self.freq.lower())

        if show_band:
            _band = atr/6.0
            for _trend in (TREND_UPWARD, TREND_DOWNWARD):
                mask = ma.make_mask(self.history.index)
                mask = ma.masked_where(trend == _trend, mask)
                chosen = ma.masked_where(~mask.mask, _band)
                top = resistance if _trend == TREND_UPWARD else support + atr
                if chosen.any():
                    # http://www.w3schools.com/html/html_colornames.asp
                    for i, color in enumerate(["darkgreen", "chartreuse", "beige", "yellow", "orange", "red"]):
                        plt.bar(top.index, chosen, width=band_width, color=color, bottom=(top - (i + 1) * _band), alpha=alpha*.3)

    def plot_show(self):
        for label in self.ax.xaxis.get_ticklabels():
            # label is a Text instance
            #label.set_color('')
            label.set_rotation(45)
            label.set_fontsize(12)
            label.set_alpha(.5)

        #handles, labels = self.ax.get_legend_handles_labels()
        #self.ax.legend(handles, labels, loc=9) # bbox_to_anchor=(0, 0, 0, 1.1), loc=9)
        self.ax.set_title(self.name)
        plt.show()


