"""LMKBandCalculators

  LMK means Livermore's Market Method. And it's a band filter method explained in the link.
  http://blessedfool.blogspot.com/2013/05/project-freedom-12-livermore-secret.html

  *LMKBandCalculatorPivot*: As pivots are calcuated based on "after fact" future tick
   it's flawed to apply to to real data and predict the future.

  *LMKBandCalculatorHeuristic*: will only base the calculator on the start pivot found
   and is suitable to apply to the real data in the sense that it makes mistakes.
"""

import math
import pandas


# the order matters, redefine to other values will have undesirable side effect
BAND_UPWARD = 6
BAND_NAT_RALLY = 5
BAND_SEC_RALLY = 4
BAND_SEC_REACT = 3
BAND_NAT_REACT = 2
BAND_DNWARD = 1
BAND_UNKNOWN = 0

TREND_UNKNOWN = -1
TREND_UP = 1
TREND_DN = 2


def normalize(band):
    if band > BAND_UPWARD:
        band = BAND_UPWARD
    if band < BAND_DNWARD:
        band = BAND_DNWARD

    return band


class LMKBandCalculatorPivot(object):
    def __init__(self, atr_factor=1.0):
        self.atr_factor = atr_factor * 2.0

        self.rsst = 0.0  # rsst => resistent
        self.sppt = 0.0  # sppt => support
        self.last_pivot = None
        self.last_water_mark = None

    def __call__(self, tick):
        # assert tick["ATR"] != 0, "ATR should not be zero."
        # RRST @ 2014-01-02, and use 0.001 to avoid dividing by zero.
        if tick["ATR"] == 0:
            tick["ATR"] = 0.001
        band_width = tick["ATR"] * self.atr_factor
        close_ = tick["Close"]

        if tick["Top"]:
            self.rsst = close_
            self.last_pivot = tick.copy()

            band = BAND_UPWARD
            trend = TREND_UP
            water_mark = self.rsst

        elif tick["Btm"]:
            self.sppt = close_
            self.last_pivot = tick.copy()

            band = BAND_DNWARD
            trend = TREND_DN
            water_mark = self.sppt

        elif self.last_pivot is not None:
            # trending downward ...
            if self.last_pivot["Top"]:
                band = normalize(6 - int(math.floor((self.rsst - close_) / (band_width / 6.0))))
                trend = TREND_DN
            # trending upward ...
            elif self.last_pivot["Btm"]:
                band = normalize(int(math.ceil((close_ - self.sppt) / (band_width / 6.0))))
                trend = TREND_UP

            # print(tick.name.strftime("%Y-%m-%d"), close_, self.last_pivot["Close"], self.rsst, self.sppt, band, band_width)

            water_mark = self.last_water_mark

            if band >= BAND_SEC_RALLY:
                if close_ > water_mark:
                    water_mark = close_
                    if band == BAND_UPWARD:
                        self.rsst = water_mark

            elif band <= BAND_SEC_REACT:
                if close_ < water_mark:
                    water_mark = close_
                    if band == BAND_DNWARD:
                        self.sppt = water_mark

        else:  # no known pivot, no defined trend...
            band = BAND_UNKNOWN
            trend = TREND_UNKNOWN
            water_mark = close_

        self.last_water_mark = water_mark

        return pandas.Series({"Trend": trend, "WM": water_mark, "Band": band})


class LMKBandCalculatorHeuristic(object):
    def __init__(self, start_pivot, atr_factor=1.0):
        self.atr_factor = atr_factor * 2.0

        # internal state
        self.rsst = 0.0  # rsst => resistent
        self.sppt = 0.0  # sppt => support
        self.start_pivot = start_pivot
        if start_pivot["Top"]:
            self.rsst = start_pivot["Close"]
            self.trend = TREND_UP
        else:
            assert start_pivot["Btm"] == True
            self.sppt = start_pivot["Close"]
            self.trend = TREND_DN

    def __call__(self, tick):
        if tick.name <= self.start_pivot.name:
            return pandas.Series({"Trend": TREND_UNKNOWN, "WM": 0, "Band": BAND_UNKNOWN})

        # assert tick["ATR"] != 0, "ATR should not be zero."
        # RRST @ 2014-01-02, and use 0.001 to avoid dividing by zero.
        if tick["ATR"] == 0:
            tick["ATR"] = 0.001
        band_width = tick["ATR"] * self.atr_factor
        close_ = tick["Close"]

        if self.trend == TREND_UP:
            band = normalize(6 - int(math.floor((self.rsst - close_) / (band_width / 6.0))))

        elif self.trend == TREND_DN:
            band = normalize(int(math.ceil((close_ - self.sppt) / (band_width / 6.0))))

        # Trend changes ...
        if band == BAND_UPWARD:
            if self.trend == TREND_DN or self.rsst < close_:
                self.rsst = close_

            self.trend = TREND_UP

        if band == BAND_DNWARD:
            if self.trend == TREND_UP or self.sppt > close_:
                self.sppt = close_

            self.trend = TREND_DN

        # after calculation ...
        if self.trend == TREND_UP:
            water_mark = self.rsst
        elif self.trend == TREND_DN:
            water_mark = self.sppt

        return pandas.Series({"Trend": self.trend, "WM": water_mark, "Band": band})
