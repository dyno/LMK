import traceback
import sys
import math

from pandas import Series

import log

#--------------------------------------------------------------------------------
# cannot be redefined to other value
BAND_UPWARD        = 6
BAND_NATURAL_RALLY = 5
BAND_SECOND_RALLY  = 4
BAND_SECOND_REACT  = 3
BAND_NATURAL_REACT = 2
BAND_DOWNWARD      = 1

TREND_UPWARD    = 2
TREND_DOWNWARD  = 1

#--------------------------------------------------------------------------------
class LivermoreMarketKeyCalculator(object):
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

#--------------------------------------------------------------------------------
class LivermoreMaketKeyBacktestCalculator(object):
    def __init__(self, fund=10000.0, commission=9.9):
        self.fund = self.cash = fund
        self.amount = 0
        self.commission = commission
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


