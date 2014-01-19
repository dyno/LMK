#!/usr/bin/env python

import sys
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

class LivermoreMarketKey(object):
    def __init__(self):
        pass

    def __call__(self, tick):
        pass
        return band

class Stock(object):
    def __init__(self, name):
        self.name = name

    def retrieve_history(self, use_cache=True, start="4/1/2010"):
        store_name = "{}.hd5".format(self.name)

        if use_cache and exists(store_name):
            self.store = HDFStore(store_name)
            self.history = self.store.get("history")
            return

        self.history = DataReader(self.name, "yahoo", start, date.today())
        self.store = HDFStore(store_name)
        self.store.put("history", self.history)
        self.store.flush()

    def process_atr(self, atr_period=14):
        calculator = ATRCalculator(atr_period)
        self.history["ATR"] = self.history.apply(calculator, axis=1)

    def process_livermore_market_key(self):
        pass

    def plot_livermore_trend(self):
        # http://matplotlib.org/examples/pylab_examples/color_by_yvalue.html
        return

        close = self.history["Close"]
        atr = self.history["ATR"]
        tLow = self.history["tLow"]
        up_trend = ma.masked_where(close > (tLow + 4.0 / 6 * atr), close)
        dn_trend = ma.masked_where(close < (tLow + 2.0 / 6 * atr), close)
        between =  ma.masked_where((close >= (tLow + 2.0 / 6 * atr)) & (close <= (tLow + 4.0 / 6 * atr)), close)

        mondays = WeekdayLocator(MONDAY)
        months  = MonthLocator(range(1,13), bymonthday=1, interval=1) # every month
        monthsFmt = DateFormatter("%b '%y")
        ax = plt.gca()
        ax.xaxis.set_major_locator(months)
        ax.xaxis.set_major_formatter(monthsFmt)
        ax.xaxis.set_minor_locator(mondays)
        ax.grid(True)

        plt.plot(self.history.index, up_trend, "r", self.history.index, dn_trend, "g", self.history.index, between, "b")
        plt.show()

def main():
    #stk = Stock("000001.SS")
    #stk = Stock("000826.SZ")
    stk = Stock("QQQ")
    stk.retrieve_history(start="4/1/2010")
    #stk.histkory = stk.histkory.loc["5/30/2008":]
    stk.process_atr()
    stk.process_livermore_market_key()
    stk.plot_livermore_trend()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    gLogger = logging.getLogger()
    stdoutStreamHandler = logging.StreamHandler(stream=sys.stdout)

    main()

