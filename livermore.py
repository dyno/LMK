#!/usr/bin/env python

import sys
import logging
from os.path import exists
from datetime import date

import numpy as np
import matplotlib.pyplot as plt
from pandas.io.data import DataReader
from pandas import HDFStore, Series
from numpy import ma, logical_and
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY

STATE_UP_TREND  = 1
STATE_NAT_RALLY = 2
STATE_SEC_RALLY = 3
STATE_DN_TRENT  = 4
STATE_NAT_REACT = 5
STATE_SEC_REACT = 6
STATE_UNKOWN    = 7

class StockPriceStateMachine(object):
    def __init__(self):
        self.state = STATE_UNKOWN #marketState
        self.up_trend    = 0
        self.dn_trend    = 0
        self.nat_rally   = 0
        self.nat_react   = 0

        #st.price_high
        #st.price_low
        #st.price_open
        #st.price_close

    def pivot():
        pass

class Stock(object):
    def __init__(self, name):
        self.name = name

    def load_data(self, use_cached=True):
        store_name = "{}.hd5".format(self.name)
        if exists(store_name):
            store = HDFStore(store_name)
            self.history = store.get("history")
            return

        self.retrieve_history()
        self.process_atr()
        store = HDFStore(store_name)
        store.put("history", self.history)
        store.flush()


    def retrieve_history(self, start="7/6/2012", end=date.today()):
        self.history = DataReader(self.name, "yahoo", start, end)

    # http://stockcharts.com/help/doku.php?id=chart_school:technical_indicators:average_true_range_a
    def process_atr(self):
        ATR_PERIOD = 14
        HL = Series(index=self.history.index)
        HCp = Series(index=self.history.index)
        LCp = Series(index=self.history.index)
        tr = Series(index=self.history.index)
        atr = Series(index=self.history.index)
        tLow = Series(index=self.history.index)

        #day 0
        day = self.history.ix[0]
        HL[0] = day["High"] - day["Low"]
        tr[0] = atr[0] = HL[0]
        tLow[0] = day["Low"]
        for i in range(1, len(self.history)):
            day = self.history.iloc[i]
            prv_day = self.history.iloc[i-1]
            HL[i] = day["High"] - day["Low"]
            HCp[i] = day["High"] - prv_day["Close"]
            LCp[i] = prv_day["Close"] - day["Low"]
            tr[i] = max(HL[i], HCp[i], LCp[i])
            tLow[i] = min(day["Low"], prv_day["Close"])
            # day 1 ~ ATR_PERIOD - 1
            if i < ATR_PERIOD:
                atr[i] = tr[:i+1].mean()

            # day ATR_PERIOD ~
            else:
                atr[i] = (atr[i-1] * (ATR_PERIOD - 1) + tr[i]) / ATR_PERIOD

        self.history["TR"] = tr
        self.history["ATR"] = atr
        self.history["HL"] = HL
        self.history["HCp"] = HCp
        self.history["LCp"] = LCp
        self.history["tLow"] = tLow

    def process_livermore_band(self):
        sm = StockPriceStateMachine()
        #intialize sm with first record
        sm.state = STATE_UP_TREND
        for p in self.history.values[1:]:
            if sm.state == STATE_UP_TREND:
                pass
            if sm.state == STATE_NAT_RALLY:
                pass
            if sm.state == STATE_SEC_RALLY:
                pass
            if sm.state == STATE_DN_TRENT:
                pass
            if sm.state == STATE_NAT_REACT:
                pass
            if sm.state == STATE_SEC_REACT:
                pass

    def plot_livermore(self):
        # http://matplotlib.org/examples/pylab_examples/color_by_yvalue.html
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
    #st = Stock("000001.SS")
    st = Stock("000826.SZ")
    #st = Stock("QQQ")
    st.load_data()
    #st.history = st.history.loc["5/30/2008":]
    st.process_atr()
    st.process_livermore_band()
    st.plot_livermore()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    gLogger = logging.getLogger()
    stdoutStreamHandler = logging.StreamHandler(stream=sys.stdout)

    main()

# 1. what is the price used in calculation?
# 2. what is the buy/sell point?

