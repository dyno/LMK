#!/usr/bin/env python

import traceback
import sys
import math
import logging
from os.path import exists
from datetime import date

import matplotlib.pyplot as plt
from pandas.io.data import DataReader
from pandas import HDFStore, Series
from numpy import ma, logical_and, mean
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY

# http://stockcharts.com/help/doku.php?id=chart_school:technical_indicators:average_true_range_a
class ATRCalculator(object):
    def __init__(self, atr_period):
        self.atr_period = atr_period
        self.tr_list = []
        self.last_tick = None
        self.atr = None

    def __call__(self, tick):
        # if not self.last_tick: # => ValueError: 'The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()'
        if not self.last_tick is None:
            HL = tick["High"] - tick["Low"]
            HCp = abs(tick["High"] - self.last_tick["Close"])
            LCp = abs(tick["Low"] - self.last_tick["Close"])
            tr = max(HL, HCp, LCp)
        else:
            tr = tick["High"] - tick["Low"]

        self.last_tick = tick

        if len(self.tr_list) < self.atr_period:
            self.tr_list.append(tr)
            self.atr = sum(self.tr_list) / len(self.tr_list)
        else:
            #self.atr = (self.atr * (atr_period - 1) + self.tr) / atr_period
            self.atr += (tr - self.atr) / self.atr_period

        return self.atr

# cannot be redefined to other value
BAND_UPWARD        = 6
BAND_NATURAL_RALLY = 5
BAND_SECOND_RALLY  = 4
BAND_SECOND_REACT  = 3
BAND_NATURAL_REACT = 2
BAND_DOWNWARD      = 1

TREND_UPWARD    = 1
TREND_DOWNWARD  = 2
class LivermoreMarketKey(object):
    def __init__(self):
        # support and resistance line
        self.upward_resistance = None
        self.rally_resistance = None
        self.react_support = None
        self.downward_support = None

        self.trend = None

    def __call__(self, tick):
        current_price = tick["Close"]

        try:
            if self.trend is None:
                self.trend = TREND_UPWARD
                self.upward_resistance = tick["High"]
                #self.downward_support = tick["Low"]
                self.band_width = tick["ATR"]
                #in case we donnot have High-Low data
                if self.band_width < 0.001:
                    self.trend = None
                    return BAND_NATURAL_RALLY

            if self.trend == TREND_UPWARD:
                level = 6 - int(math.ceil((self.upward_resistance - current_price) / (self.band_width / 6)))
            if self.trend == TREND_DOWNWARD:
                level = int(math.ceil((current_price - self.downward_support) / (self.band_width / 6)))

            if level >= BAND_UPWARD:
                level = BAND_UPWARD
                #if self.upward_resistance < current_price:
                #    self.upward_resistance = current_price
                self.upward_resistance = current_price
                self.trend = TREND_UPWARD

            if level <= BAND_DOWNWARD:
                level = BAND_DOWNWARD
                #if (self.downward_support is None) or (self.downward_support > current_price):
                #    self.downward_support = current_price
                self.downward_support = current_price
                self.trend = TREND_DOWNWARD

            self.level = level
            self.band_width = tick["ATR"]

            #print "%s \n %s" % (tick, repr(self.__dict__))
            return self.level

        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print exc_type, exc_value
            #traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
            print repr(traceback.extract_tb(exc_traceback))

        print "not here! stk=%s tick=%s" % (repr(self.__dict__), repr(tick))
        sys.exit(0)

class Stock(object):
    def __init__(self, name):
        self.name = name

    def retrieve_history(self, use_cache=True, start="12/1/2013", end=date.today()):
        store_name = "{}.hd5".format(self.name)

        if use_cache and exists(store_name):
            self.store = HDFStore(store_name)
            self.history = self.store.get("history")
            return

        self.history = DataReader(self.name, "yahoo", start, end)
        self.store = HDFStore(store_name)
        self.store.put("history", self.history)
        self.store.flush()

    def process_atr(self, atr_period=14):
        calculator = ATRCalculator(atr_period)
        self.history["ATR"] = self.history.apply(calculator, axis=1)

    def process_livermore_market_key(self):
        lmk = LivermoreMarketKey()
        self.history["level"] = self.history.apply(lmk, axis=1)

    def plot_livermore_trend(self):
        # http://matplotlib.org/examples/pylab_examples/color_by_yvalue.html

        close = self.history["Close"]
        atr = self.history["ATR"]
        level = self.history["level"]
        up_trend = ma.masked_where(level < BAND_UPWARD, close)
        dn_trend = ma.masked_where(level > BAND_DOWNWARD, close)
        between =  ma.masked_where((level ==  BAND_DOWNWARD) | (level == BAND_UPWARD), close)

        mondays = WeekdayLocator(MONDAY)
        months  = MonthLocator(range(1,13), bymonthday=1, interval=1) # every month
        monthsFmt = DateFormatter("%b '%y")
        ax = plt.gca()
        ax.xaxis.set_major_locator(months)
        ax.xaxis.set_major_formatter(monthsFmt)
        ax.xaxis.set_minor_locator(mondays)
        ax.grid(True)

        plt.plot(self.history.index, up_trend, "green", self.history.index, dn_trend, "red", self.history.index, between, "blue")
        plt.show()

def main():
    stk = Stock("000001.SS")
    #stk.retrieve_history(use_cache=False, start="1/1/2007", end="1/1/2011")
    stk = Stock("000826.SZ")
    stk = Stock("300027.SZ")
    #stk = Stock("QQQ")
    #stk = Stock("VMW")
    #stk = Stock("GOOG")
    stk.retrieve_history(use_cache=False, start="4/19/2009")
    #stk.histkory = stk.histkory.loc["5/30/2008":]
    stk.process_atr()
    stk.process_livermore_market_key()
    stk.plot_livermore_trend()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    gLogger = logging.getLogger()
    stdoutStreamHandler = logging.StreamHandler(stream=sys.stdout)

    main()

