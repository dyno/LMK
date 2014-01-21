#!/usr/bin/env python

import traceback
import sys
import math
import logging
from os.path import exists
from datetime import date

import matplotlib.pyplot as plt
from pandas.io.data import DataReader
from pandas import HDFStore, Series, DataFrame
from numpy import ma, logical_and, mean
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY

#--------------------------------------------------------------------------------
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

#--------------------------------------------------------------------------------
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
        self.trend = None
        # support and resistance line
        self.upward_resistance = None
        self.downward_support = None

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
                self.upward_resistance = current_price
                self.trend = TREND_UPWARD

            if level <= BAND_DOWNWARD:
                level = BAND_DOWNWARD
                self.downward_support = current_price
                self.trend = TREND_DOWNWARD

            self.level = level
            self.band_width = tick["ATR"]
            #gLogger.debug(type(tick))
            #sys.exit(0)
            return self.level
        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            gLogger.debug("%s :: %s", exc_type, exc_value)
            gLogger.debug(traceback.extract_tb(exc_traceback))

        gLogger.debug("NOT_REACHED! stk=%s tick=%s", repr(self.__dict__), repr(tick))
        sys.exit(0)

class LMKBacktest(object):
    def __init__(self):
        self.fund = 10000.0
        self.cash = self.fund
        self.amount = 0
        self.commission = 9.9
        self.price = None
        self.buy_price = None
        self.sell_price = None
        self.try_first_hand = True
        self.last_value_rate = None

    def __call__(self, tick):
        self.price = tick["Close"]
        try:
            #if int(tick["level"]) == BAND_UPWARD:
            #if int(tick["level"]) >= BAND_SECOND_RALLY:
            if int(tick["level"]) >= BAND_SECOND_REACT:
                #buy
                amount = int(self.cash / self.price)
                if amount > 0:
                    if self.try_first_hand:
                        #if tick["level"] < BAND_UPWARD:
                        amount /= 2
                        #else: # wait for the second upward signal
                        #    amount = 0
                    else:
                        if tick["level"] < BAND_UPWARD:
                            amount = 0 # second signal should upward

                    self.try_first_hand = False

                    if amount > 0:
                        self.amount += amount
                        self.cash -= (amount * self.price + self.commission)
                        self.buy_price = self.price
                        value_rate = self.value_rate()
                        gLogger.debug("%s: BUY  %d @%.2f = %.2f %s" % (
                                      tick.name, amount, self.buy_price, value_rate,
                                      "PROFIT" if value_rate >= self.last_value_rate else "LOSS"))
                        self.last_value_rate = value_rate
                        #raise Exception("BUY")

            self.first_skipped = True

            #if int(tick["level"]) == BAND_DOWNWARD:
            if int(tick["level"]) <= BAND_NATURAL_REACT:
                self.first_skipped = True
                self.try_first_hand = True
                amount = self.amount
                cut_loss = False
                if amount > 0:
                    if self.price <= self.buy_price / (1 + .05): # cut loss
                        self.sell_price = self.buy_price / (1 + .05)
                        cut_loss = True
                    else:
                        self.sell_price = self.price

                    if tick["level"] > BAND_DOWNWARD and not cut_loss:
                        amount /= 2

                    self.cash += (amount * self.price - self.commission)
                    self.amount -= amount
                    value_rate = self.value_rate()
                    gLogger.debug("%s: SELL %d @%.2f = %.2f %s %s" % (
                                  tick.name, amount, self.sell_price, value_rate,
                                  "CUT_LOSS" if cut_loss else "",
                                  "PROFIT" if value_rate >= self.last_value_rate else "LOSS"))
                    self.last_value_rate = value_rate

            return self.value_rate()
        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            gLogger.debug("%s :: %s", exc_type, exc_value)
            gLogger.debug(traceback.extract_tb(exc_traceback))

    def value_rate(self):
        return (self.amount * self.price + self.cash) / self.fund

#--------------------------------------------------------------------------------
class Stock(object):
    def __init__(self, name, freq="W", atr_period=15):
        self.name = name
        self.atr_period = atr_period # default 3 weeks
        self.freq = freq # D : daily, W : weekly

    def retrieve_history(self, use_cache=True, start="12/1/2013", end=date.today()):
        store_name = "{}.hd5".format(self.name)

        if use_cache and exists(store_name):
            self.store = HDFStore(store_name)
            self.history_daily = self.store.get("history")
        else:
            self.history_daily = DataReader(self.name, "yahoo", start, end)
            self.store = HDFStore(store_name)
            self.store.put("history", self.history_daily)
            self.store.flush()

        self.history = self.history_daily

        if self.freq == "W":
            self.atr_period /= 5 # 3 weeks
            self.history_weekly = DataFrame(self.history_daily["Close"].resample("W-FRI", how="last"), columns=("Close",))
            self.history_weekly["Open"] = self.history_daily["Open"].resample("W-FRI", how="first")
            self.history_weekly["High"] = self.history_daily["High"].resample("W-FRI", how="max")
            self.history_weekly["Low"] = self.history_daily["Low"].resample("W-FRI", how="min")
            # e.g. the spring festival week
            self.history_weekly.fillna(method="ffill", inplace=True)
            self.history = self.history_weekly

    def process_atr(self):
        calculator = ATRCalculator(self.atr_period)
        self.history["ATR"] = self.history.apply(calculator, axis=1)

    def process_livermore_market_key(self):
        lmk = LivermoreMarketKey()
        self.history["level"] = self.history.apply(lmk, axis=1)

    def process_backtest(self):
        backtest = LMKBacktest()
        self.history["value"] = self.history.apply(backtest, axis=1)
        gLogger.info("profit=%.2f%%", (backtest.value_rate() - 1) * 100)

    def plot_livermore_trend(self):
        # http://matplotlib.org/examples/pylab_examples/color_by_yvalue.html
        mondays = WeekdayLocator(MONDAY)
        months  = MonthLocator(range(1, 13), bymonthday=1, interval=1) # every month
        #monthsFmt = DateFormatter("%b '%y")
        #monthsFmt = DateFormatter("%b")
        monthsFmt = DateFormatter("%y%m")
        dayFmt = DateFormatter("%d")
        ax = plt.gca()
        ax.xaxis.set_major_locator(months)
        ax.xaxis.set_major_formatter(monthsFmt)
        ax.xaxis.set_minor_locator(mondays)
        #ax.xaxis.set_minor_formatter(dayFmt)
        ax.grid(True)

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

        for band in range(BAND_DOWNWARD, BAND_UPWARD + 1):
            mask = ma.make_mask(self.history.index)
            mask = ma.masked_where(level == band, mask)
            chosen = ma.masked_where(~mask.mask, close)
            if chosen.any():
                plt.plot(self.history.index, chosen, style_dict[band], label="%s" % band)

        # upward trend
        mask = ma.make_mask(self.history.index)
        #mask = ma.masked_where(level >= BAND_SECOND_RALLY, mask)
        mask = ma.masked_where(level >= BAND_SECOND_REACT, mask)
        chosen = ma.masked_where(~mask.mask, close)
        if chosen.any():
            plt.plot(self.history.index, chosen, "g-")

        # downward trend
        mask = ma.make_mask(self.history.index)
        mask = ma.masked_where(level <= BAND_SECOND_REACT, mask)
        chosen = ma.masked_where(~mask.mask, close)
        if chosen.any():
            plt.plot(self.history.index, chosen, "r-")

        plt.show()

def main():
    #stk = Stock("000001.SS", freq="W")
    #stk = Stock("002024.SZ")
    #stk = Stock("000826.SZ")
    #stk.retrieve_history(use_cache=False, start="7/16/2005", freq="W")
    #stk.retrieve_history(use_cache=False, start="2/15/2007", freq="W")

    #stk = Stock("600085.SS") # Tong Ren Tang
    #stk = Stock("300052.SZ") # Zhong Qing Bao
    #stk = Stock("300027.SZ") # Huayi Brothers Media Corp

    #stk = Stock("GOOG")
    #stk = Stock("AAPL")
    #stk = Stock("AMZN")

    #stk = Stock("YELP")
    #stk = Stock("TWTR")
    #stk = Stock("TSLA", freq="D")
    #stk = Stock("TSLA", freq="W") # ***

    #stk = Stock("VMW", freq="W")
    #stk = Stock("CTXS", freq="D")
    #stk = Stock("ORCL", freq="D")

    stk = Stock("EDU") # ***
    #stk = Stock("YOKU")

    # QQQ is used to verify the correction of ATR calculation
    #stk = Stock("QQQ")
    #stk.retrieve_history(use_cache=False, start="12/1/2013")
    stk.retrieve_history(use_cache=False, start="6/1/2013")

    stk.process_atr()
    stk.process_livermore_market_key()
    stk.process_backtest()
    stk.plot_livermore_trend()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    gLogger = logging.getLogger()
    stdoutStreamHandler = logging.StreamHandler(stream=sys.stdout)

    main()

