import traceback
import sys
import math

import numpy as np
import matplotlib.pyplot as plt
from pandas import Series
from numpy import ma

import log
from constants import *

#--------------------------------------------------------------------------------
class LMKBandCalculator(object):
    def __init__(self, state):
        self.atr_factor = state.atr_factor
        self.level = state.band

        self.trend = TREND_UPWARD if self.level >= BAND_SEC_RALLY else TREND_DNWARD
        # support and resistance line
        self.upward_resistance = state.peak.value
        self.downward_support = state.valley.value
        self.band_width = None

    def __call__(self, tick):
        current_price = tick["Close"]
        if self.band_width is None:
            self.band_width = tick["ATR"] * self.atr_factor

        try:
            if self.trend == TREND_UPWARD:
                level = 6 - int(math.floor((self.upward_resistance - current_price) / (self.band_width / 6.0)))
            if self.trend == TREND_DNWARD:
                level = int(math.ceil((current_price - self.downward_support) / (self.band_width / 6.0)))

            if level >= BAND_UPWARD:
                if self.upward_resistance < current_price \
                        or self.trend == TREND_DNWARD: # reset
                    self.upward_resistance = current_price

                level = BAND_UPWARD
                self.trend = TREND_UPWARD

            if level <= BAND_DNWARD:
                if self.downward_support > current_price \
                        or self.trend == TREND_UPWARD: # reset
                    self.downward_support = current_price

                level = BAND_DNWARD
                self.trend = TREND_DNWARD

            self.level = level
            self.band_width = tick["ATR"] * self.atr_factor

            return Series ({
                        "trend": self.trend,
                        "level": self.level,
                        "resistance": self.upward_resistance,
                        "support": self.downward_support,
                   })
        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            log.logger.debug("%s :: %s", exc_type, exc_value)
            log.logger.debug(traceback.extract_tb(exc_traceback))

        log.logger.debug("NOT_REACHED()! stk=%s tick=%s", repr(self.__dict__), repr(tick))


def plot_lmk_band(history, atr_factor=2.0, line="-", alpha=1.0, show_band=False, band_width=1, show_volume=True, fluct_factor=2):
        # http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.plot
        style_dict = {
            BAND_DNWARD     : "rv",
            BAND_NAT_REACT  : "m<",
            BAND_SEC_REACT  : "m*",
            BAND_SEC_RALLY  : "c*",
            BAND_NAT_RALLY  : "c>",
            BAND_UPWARD     : "g^",
        }

        close = history["Close"]
        volume = history["Volume"]
        atr = history["ATR"] * atr_factor
        level = history["level"]
        trend = history["trend"]
        resistance = history["resistance"]
        support = history["support"]

        ax = plt.gca()
        ax.set_xmargin(0.02)
        #ax.set_ymargin(0.2)
        min_close = min(close)
        height = min_close * fluct_factor
        ymin =  min_close - height / 4.0 #
        ymax = ymin + height # ymax - ymin = min_close * 2 + (min_close * 2 / 4.0)
        ax.set_ylim(ymin, ymax)

        for band in range(BAND_DNWARD, BAND_UPWARD + 1):
            mask = ma.make_mask(history.index)
            mask = ma.masked_where(level == band, mask)
            chosen = ma.masked_where(~mask.mask, close)
            # "ValueError: putmask: mask and data must be the same size" is a numpy bug.
            # using virtual env.
            if chosen.any():
                ax.plot(history.index, chosen, style_dict[band], alpha=alpha)

        #the ODR
        mask = ma.make_mask(history.index)
        mask = ma.masked_where(history["ODR"] == True, mask)
        chosen = ma.masked_where(~mask.mask, close)
        if chosen.any():
            ax.plot(history.index, chosen, "ro", alpha=alpha*1.1)

        #print ax.get_xlim()
        ax2 = plt.gca().twinx()
        ymax = max(volume) * 5
        ymin = min(volume)
        ax2.set_ylim(ymin, ymax)

        ax2.set_xlim(ax.get_xlim())
        ax2.get_xaxis().set_visible(False)

        # upward trend
        mask = ma.make_mask(history.index)
        mask = ma.masked_where(level >= BAND_SEC_RALLY, mask)
        #mask = ma.masked_where(level >= BAND_SEC_REACT, mask)
        chosen = ma.masked_where(~mask.mask, close)
        chosen_volume = ma.masked_where(~mask.mask, volume)
        # warnings.warn("Warning: converting a masked element to nan.")
        chosen_volume = ma.filled(chosen_volume, 0)
        if chosen.any():
            ax.plot(history.index, chosen, "g%s" % line, alpha=alpha)
            ax2.bar(history.index, chosen_volume, width=band_width, align="center", color="g", alpha=.5)

        # downward trend
        mask = ma.make_mask(history.index)
        mask = ma.masked_where(level <= BAND_SEC_REACT, mask)
        #mask = ma.masked_where(level <= BAND_SEC_RALLY, mask)
        chosen = ma.masked_where(~mask.mask, close)
        chosen_volume = ma.masked_where(~mask.mask, volume)
        chosen_volume = ma.filled(chosen_volume, 0)
        if chosen.any():
            ax.plot(history.index, chosen, "r%s" % line, alpha=alpha)
            ax2.bar(history.index, chosen_volume, width=band_width, align="center", color="r", alpha=.5)

        if show_band:
            top = history.apply(lambda r: r["resistance"] if r["trend"] == TREND_UPWARD else r["support"] + r["ATR"] * atr_factor, axis=1)
            for _trend in (TREND_UPWARD, TREND_DNWARD):
                mask = ma.make_mask(history.index)
                mask = ma.masked_where(trend == _trend, mask)
                height =  atr / 6.0
                if chosen.any():
                    # http://www.w3schools.com/html/html_colornames.asp
                    for i, color in enumerate(["darkgreen", "chartreuse", "beige", "yellow", "orange", "red"]):
                        ax.bar(top.index, height, bottom=(top - (i + 1) * height),
                                width=band_width, align="edge", color=color, edgecolor=color, alpha=alpha * .2)


#--------------------------------------------------------------------------------
class LMKBandBacktestCalculator(object):
    def __init__(self, fund=10000.0, commission=9.9):
        self.fund = self.cash = fund
        self.amount = 0
        self.commission = commission
        self.price = None
        self.buy_price = None
        self.sell_price = None
        self.try_first_hand = True
        self.last_value_rate = None
        self.first_trend_skipped = False

    def __call__(self, tick):
        self.price = tick["Close"]
        try:
            #if int(tick["level"]) == BAND_UPWARD:
            #if int(tick["level"]) >= BAND_NAT_RALLY:
            if int(tick["level"]) >= BAND_SEC_RALLY:
                if not self.first_trend_skipped: return

            #if int(tick["level"]) >= BAND_SEC_REACT:
                amount = int(self.cash / self.price)
                if amount > 0:
                    if self.try_first_hand:
                        #if tick["level"] < BAND_UPWARD:
                        amount /= 2
                        #else: # wait for the second upward signal
                        #    amount = 0
                    else:
                        if tick["level"] < BAND_UPWARD:
                            # second signal should confirm the upward trend
                            amount = 0

                    self.try_first_hand = False

                    if amount > 0:
                        self.amount += amount
                        self.cash -= (amount * self.price + self.commission)
                        self.buy_price = self.price
                        value_rate = self.value_rate()
                        log.logger.debug("%s: BUY  %d @%.2f = %.2f %s" % (
                                      tick.name, amount, self.buy_price, value_rate,
                                      "PROFIT" if value_rate >= self.last_value_rate else "LOSS"))
                        self.last_value_rate = value_rate

            #if int(tick["level"]) == BAND_DNWARD:
            #if int(tick["level"]) <= BAND_NAT_REACT:
            if int(tick["level"]) <= BAND_SEC_REACT:
                self.first_trend_skipped = True

                self.try_first_hand = True
                amount = self.amount
                cut_loss = False
                if amount > 0:
                    if self.price <= self.buy_price / (1 + .07): # cut loss
                        self.sell_price = self.buy_price / (1 + .07)
                        cut_loss = True
                    else:
                        self.sell_price = self.price

                    #if tick["level"] > BAND_DNWARD and not cut_loss:
                    #    amount /= 2

                    self.cash += (amount * self.price - self.commission)
                    self.amount -= amount
                    value_rate = self.value_rate()
                    log.logger.debug("%s: SELL %d @%.2f = %.2f %s %s" % (
                                  tick.name, amount, self.sell_price, value_rate,
                                  "CUT_LOSS" if cut_loss else "",
                                  "PROFIT" if value_rate >= self.last_value_rate else "LOSS"))
                    self.last_value_rate = value_rate

            return self.value_rate()
        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            log.logger.debug("%s :: %s", exc_type, exc_value)
            log.logger.debug(traceback.extract_tb(exc_traceback))

    def value_rate(self):
        return (self.amount * self.price + self.cash) / self.fund

if __name__ == "__main__":
    import sys

    #import warnings
    #warnings.simplefilter('error', UserWarning)

    import pandas
    from pandas.io.data import DataReader

    from ATRCalculator import ATRCalculator
    from InitialPivotalPointCalculator import InitialPivotalPointCalculator
    from common import show_plot, probe_proxy
    from stock import Stock

    probe_proxy()
    log.init()

    #stk = Stock("^GSPC")
    #stk.retrieve_history(start="2012/1/1", use_cache=False, no_volume=True)
    #stk = Stock("002237.SZ")
    #stk.retrieve_history(start="2013/1/1", use_cache=True, no_volume=False)
    stk = Stock("WUBA")
    stk.retrieve_history(start="2013/6/1", use_cache=False, no_volume=False)

    history = stk.history
    atr_factor = 2.0

    #history = DataReader("000001.SS", "yahoo", start="2012/9/1")
    #history = DataReader("AAPL", "yahoo", start="2012/9/1")
    #history = DataReader("TWTR", "yahoo", start="2012/9/1")
    #history = DataReader("FB", "yahoo", start="2012/9/1")
    #history = DataReader("AMZN", "yahoo", start="2013/9/1")
    #history = DataReader("TSLA", "yahoo", start="2012/9/1")
    #history = DataReader("VMW", "yahoo", start="2012/9/1")
    #history.dropna(axis=0, inplace=True)

    c = ATRCalculator(atr_period=14)
    history["ATR"] = history.apply(c, axis=1)
    history.fillna(method="backfill", axis=0, inplace=True)

    stk.resample_history(freq="W-FRI")
    history = stk.history

    c = InitialPivotalPointCalculator(atr_factor=atr_factor)
    #c = InitialPivotalPointCalculator(atr_factor=1)
    #c = InitialPivotalPointCalculator(atr_factor=1.5)
    history.apply(c, axis=1)

    c = LMKBandCalculator(c)
    lmk_band = history.apply(c, axis=1)
    history = pandas.merge(history, lmk_band, left_index=True, right_index=True, sort=False)

    #c = LMKBandBacktestCalculator()
    #history.apply(c, axis=1)

    plot_lmk_band(history, atr_factor=atr_factor, show_band=True, band_width=7)
    show_plot()


