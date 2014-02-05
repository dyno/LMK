import traceback
import sys

import numpy as np
import matplotlib.pyplot as plt
from pandas import Series
from numpy import ma

import log
from constants import *

#--------------------------------------------------------------------------------
class State(object):
    def __setattr__(self, name, val):
        if name in ("upward_pivotal", "dnward_pivotal", "rally_resistance", "reaction_support"):
            self.__dict__["recorded"] = True

        self.__dict__[name] = val

class LMKCalculator(object):
    def __init__(self, state):
        self.state = State()

        self.state.atr_factor = state.atr_factor
        self.state.band = state.band
        self.state.upward_pivotal = state.peak.value
        self.state.dnward_pivotal = state.valley.value
        # support and resistance line => rally or reaction extremum
        self.state.rally_resistance = self.state.upward_pivotal
        self.state.reaction_support = self.state.dnward_pivotal

    def __call__(self, tick):
        state = self.state
        state.recorded = False
        current_price = tick["Close"]
        band_width = tick["ATR"] * state.atr_factor

        try:
            if state.band == BAND_UPWARD:
                if current_price >= state.upward_pivotal:
                    #10(a) => BAND_UPWARD
                    state.band = BAND_UPWARD
                    state.upward_pivotal = current_price

                if current_price < state.upward_pivotal - band_width:
                    # 4(a), 6(a), 10(b) => BAND_NAT_REACT
                    state.band = BAND_NAT_REACT
                    state.reaction_support = current_price

            elif state.band == BAND_NAT_RALLY:
                if current_price <= state.rally_resistance - band_width:
                    if current_price <= state.dnward_pivotal:
                        # 4(d) => BAND_DNWARD
                        state.band = BAND_DNWARD
                        state.dnward_pivotal = current_price
                    elif current_price > state.reaction_support:
                        # 6(h) => BAND_SEC_REACT
                        state.band = BAND_SEC_REACT
                    else:
                        # 6(b) => BAND_NAT_REACT
                        state.band = BAND_NAT_REACT
                        if state.reaction_support > current_price:
                            state.reaction_support = current_price

                elif current_price > state.rally_resistance:
                    if current_price > state.rally_resistance + band_width / 2 or \
                            current_price > state.upward_pivotal:
                        state.band = BAND_UPWARD
                        # 5(a), 6(d), 6(f) => BAND_UPWARD
                        #if current_price > state.upward_pivotal:
                        state.upward_pivotal = current_price
                    else:
                        # 6(c) => BAND_NAT_RALLY
                        state.band = BAND_NAT_RALLY
                        state.rally_resistance = current_price

            elif state.band == BAND_SEC_RALLY:
                if current_price >= state.rally_resistance + 0.5 * band_width: #upward_pivotal:
                    # 6(d), 6(f), 5(a) => BAND_UPWARD
                    state.band = BAND_UPWARD
                    state.upward_pivotal = current_price

                elif current_price >= state.rally_resistance:
                    # 6(g) => BAND_NAT_RALLY
                    state.band = BAND_NAT_RALLY
                    state.rally_resistance = current_price

                elif current_price < state.rally_resistance - 1.5 * band_width: #dnward_pivotal:
                    # 6(b) => BAND_DNWARD
                    state.band = BAND_DNWARD
                    state.dnward_pivotal = current_price
                elif current_price < state.rally_resistance - band_width:
                    # 4(d), 6(b) => BAND_NAT_REACT
                    state.band = BAND_NAT_REACT

            elif state.band == BAND_SEC_REACT:
                if current_price <= state.reaction_support - 0.5 * band_width: #state.dnward_pivotal:
                    # 6(b) => BAND_DNWARD
                    state.band = BAND_DNWARD
                    state.dnward_pivotal = current_price

                elif current_price <= state.reaction_support:
                    # 6(h) => BAND_NAT_REACT
                    state.band = BAND_NAT_REACT
                    state.reaction_support = current_price

                elif current_price >= state.reaction_support + 1.5 * band_width:
                    # 6(d) => BAND_UPWARD
                    state.band = BAND_UPWARD
                    state.upward_pivotal = current_price

                elif current_price >= state.reaction_support + band_width: #rally_resistance:
                    # 4(b), 6(d) => BAND_NAT_RALLY
                    state.band = BAND_NAT_RALLY
                    state.rally_resistance = current_price

            elif state.band == BAND_NAT_REACT:
                if current_price >= state.reaction_support + band_width:
                    if current_price >= state.upward_pivotal:
                        # 4(b), 6(d) => BAND_UPWARD
                        state.band = BAND_UPWARD
                        state.upward_pivotal = current_price
                    elif current_price < state.rally_resistance:
                        # 6(g) => BAND_SEC_RALLY
                        state.band = BAND_SEC_RALLY
                    else:
                        # 4(b), 6(d) => BAND_NAT_RALLY
                        state.band = BAND_NAT_RALLY
                        # assert(current_price > state.rally_resistance)
                        state.rally_resistance = current_price

                elif current_price < state.reaction_support - band_width / 2:
                        # 5(b) => BAND_DNWARD
                        state.band = BAND_DNWARD
                        #if current_price < state.dnward_pivotal:
                        state.dnward_pivotal = current_price
                else:
                    # 6(a), 6(b) => BAND_NAT_REACT
                    state.band = BAND_NAT_REACT
                    if current_price < state.dnward_pivotal:
                        # 6(e) => BANd_DNWARD
                        state.band = BAND_DNWARD
                        state.dnward_pivotal = current_price
                    elif current_price < state.reaction_support:
                        state.reaction_support = current_price

            elif state.band == BAND_DNWARD:
                if current_price >= state.dnward_pivotal + band_width:
                    #4(c), 6(c) => BAND_NAT_RALLY
                    state.band = BAND_NAT_RALLY
                    #if current_price > state.rally_resistance:
                    state.rally_resistance = current_price

                elif current_price < state.dnward_pivotal:
                    state.band = BAND_DNWARD
                    state.dnward_pivotal = current_price

            ## ur -> upward resistance
            ## rr -> rally resistance
            ## rs -> reaction support
            ## ds -> downward support
            if state.band == BAND_UPWARD:
                ur = state.upward_pivotal
                rr = state.upward_pivotal - band_width * 0.5 #np.NaN
                rs = state.upward_pivotal - band_width
                ds = state.upward_pivotal - band_width * 1.5
            elif state.band == BAND_NAT_RALLY:
                ur = state.rally_resistance + band_width * 0.5
                rr = state.rally_resistance
                rs = state.rally_resistance - band_width
                ds = state.rally_resistance - band_width * 1.5
            elif state.band == BAND_SEC_RALLY:
                ur = state.rally_resistance + band_width * 0.5
                rr = state.rally_resistance
                rs = state.rally_resistance - band_width
                ds = state.rally_resistance - band_width * 1.5
            elif state.band == BAND_SEC_REACT:
                ur = state.reaction_support + band_width * 1.5
                rr = state.reaction_support + band_width
                rs = state.reaction_support
                ds = state.reaction_support - band_width * 0.5
            elif state.band == BAND_NAT_REACT:
                ur = state.reaction_support + band_width * 1.5
                rr = state.reaction_support + band_width
                rs = state.reaction_support
                ds = state.reaction_support - band_width * 0.5
            elif state.band == BAND_DNWARD:
                ur = state.dnward_pivotal + band_width * 1.5
                rr = state.dnward_pivotal + band_width
                rs = state.dnward_pivotal + band_width * 0.5 #np.NaN
                ds = state.dnward_pivotal

            return Series ({"band": state.band,
                        "recorded": state.recorded,
                        "upward_pivotal": ur,
                        "rally_resistance": rr,
                        "reaction_support": rs,
                        "dnward_pivotal": ds, })
        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            log.logger.debug("%s :: %s", exc_type, exc_value)
            log.logger.debug(traceback.extract_tb(exc_traceback))

        log.logger.debug("NOT_REACHED()! stk=%s tick=%s", repr(self.__dict__), repr(tick))


def plot_lmk(history):
    style_dict = {
        BAND_DNWARD     : "rv",
        BAND_NAT_REACT  : "m<",
        BAND_SEC_REACT  : "m*",
        BAND_SEC_RALLY  : "c*",
        BAND_NAT_RALLY  : "c>",
        BAND_UPWARD     : "g^",
    }

    for band in range(BAND_DNWARD, BAND_UPWARD + 1):
        mask = ma.make_mask(history.index)
        mask = ma.masked_where((history["band"] == band) & (history["recorded"] == True), mask)
        chosen = ma.masked_where(~mask.mask, history["Close"])
        if chosen.any():
            plt.plot(history.index, chosen, style_dict[band])

        mask = ma.make_mask(history.index)
        mask = ma.masked_where((history["band"] == band) & (history["recorded"] == False), mask)
        chosen = ma.masked_where(~mask.mask, history["Close"])
        if chosen.any():
            plt.plot(history.index, chosen, style_dict[band], alpha=.2)

    style_dict = {"ur": "g-", "rr": "c-", "rs":"m-", "ds":"r-"}
    series = {"ur": history["upward_pivotal"], "rr": history["rally_resistance"],
              "rs": history["reaction_support"], "ds": history["dnward_pivotal"]}

    for line in ("ur", "rr", "rs", "ds"):
        mask = ma.make_mask(history.index)
        #mask = ma.masked_where(np.isfinite(line), mask)
        chosen = ma.masked_invalid(series[line])
        if chosen.any():
            plt.plot(history.index, chosen, style_dict[line], drawstyle="steps-mid", alpha=.5)


#--------------------------------------------------------------------------------
class LMKBacktestCalculator(object):
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
            #if int(tick["band"]) == BAND_UPWARD:
            if int(tick["band"]) >= BAND_SEC_RALLY:
                if not self.first_trend_skipped: return

            #if int(tick["band"]) >= BAND_SEC_REACT:
                amount = int(self.cash / self.price)
                if amount > 0:
                    if self.try_first_hand:
                        #if tick["band"] < BAND_UPWARD:
                        amount /= 2
                        #else: # wait for the second upward signal
                        #    amount = 0
                    else:
                        if tick["band"] < BAND_UPWARD:
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

            #if int(tick["band"]) == BAND_DNWARD:
            if int(tick["band"]) <= BAND_NAT_REACT:
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

                    if tick["band"] > BAND_DNWARD and not cut_loss:
                        amount /= 2

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
    import pandas
    import matplotlib.pyplot as plt
    from pandas.io.data import DataReader

    from ATRCalculator import ATRCalculator
    from InitialPivotalPointCalculator import InitialPivotalPointCalculator
    from common import show_plot
    from stock import Stock

    log.init()

    #stk = Stock("000001.SS")
    stk = Stock("^GSPC")
    stk.retrieve_history(start="2000/1/1", use_cache=False, no_volume=True)
    #stk = Stock("VMW")
    #stk.retrieve_history(start="2013/1/1", use_cache=False, no_volume=False)

    history = stk.history
    atr_factor = 1.0

    #history = DataReader("AAPL", "yahoo", start="2012/9/1")
    #history = DataReader("TWTR", "yahoo", start="2012/9/1")
    #history = DataReader("FB", "yahoo", start="2012/9/1")
    #history = DataReader("AMZN", "yahoo", start="2012/9/1")
    #history = DataReader("TSLA", "yahoo", start="2012/9/1")
    #history = DataReader("VMW", "yahoo", start="2012/9/1")

    #history.dropna(axis=0, inplace=True)
    c = ATRCalculator(atr_period=14)
    history["ATR"] = history.apply(c, axis=1)
    history.fillna(method="backfill", axis=0, inplace=True)

    stk.resample_history(freq="W-FRI")
    history = stk.history

    c = InitialPivotalPointCalculator(atr_factor=atr_factor)
    history.apply(c, axis=1)

    c = LMKCalculator(c)
    lmk = history.apply(c, axis=1)
    history = pandas.merge(history, lmk, left_index=True, right_index=True, sort=False)

    c = LMKBacktestCalculator()
    history.apply(c, axis=1)

    plot_lmk(history)
    show_plot()


