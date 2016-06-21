"""LMKBandCalculators

  LMK means Livermore's Market Method. And it's a band filter method explained in the link.
  http://blessedfool.blogspot.com/2013/05/project-freedom-12-livermore-secret.html

  *LMKBandCalculatorPivot*: As pivots are calcuated based on "after fact" future tick
   it's flawed to apply to to real data and predict the future.

  *LMKBandCalculatorHeuristic*: will only base the calculator on the first pivot found
   and is suitable to apply to the real data.
"""

import math
import pandas


# the order matters, redefine to other values will have undesirable side effect
BAND_UPWARD     = 6
BAND_NAT_RALLY  = 5
BAND_SEC_RALLY  = 4
BAND_SEC_REACT  = 3
BAND_NAT_REACT  = 2
BAND_DNWARD     = 1
BAND_UNKNOWN    = 0

class LMKBandCalculatorPivot(object):
    def __init__(self, atr_factor=1.0):
        self.atr_factor = atr_factor * 2.0

        self.rsst = 0.0 # rsst => resistent
        self.sppt = 0.0 # sppt => support
        self.last_pivot = None
        self.last_water_mark = None

    def __call__(self, tick):
        def normalize(band):
            if band > BAND_UPWARD: band = BAND_UPWARD
            if band < BAND_DNWARD: band = BAND_DNWARD

            return band

        #-----------------------------------------------------------------------
        #assert tick["ATR"] != 0, "ATR should not be zero."
        # RRST @ 2014-01-02, and use 0.001 to avoid dividing by zero.
        if tick["ATR"] == 0:
            tick["ATR"] = 0.001
        band_width = tick["ATR"] * self.atr_factor
        close_ = tick["Close"]

        if tick["Top"]:
            band = BAND_UPWARD
            self.rsst = close_
            water_mark = self.rsst
            self.last_pivot = tick.copy()

        elif tick["Btm"]:
            band = BAND_DNWARD
            self.sppt = close_
            water_mark = self.sppt
            self.last_pivot = tick.copy()

        elif self.last_pivot:
            # trending downward ...
            if self.last_pivot["Top"]:
                band = normalize(6 - int(math.floor((self.rsst - close_) / (band_width / 6.0))))
            # trending upward ...
            elif self.last_pivot["Btm"]:
                band = normalize(int(math.ceil((close_ - self.sppt) / (band_width / 6.0))))

            env.logger.debug("%s=>close_=%.2f, from %s, rsst=%.2f, sppt=%.2f, band=%d, band_width=%.2f",
                             tick.name.strftime("%Y-%m-%d"), close_, self.last_pivot["Close"], self.rsst, self.sppt, band, band_width)

            if band >= BAND_SEC_RALLY:
                if close_ > water_mark:
                    water_mark = close_
                    if band == BAND_UPWARD:
                        self.rsst = water_mark

            if band <= BAND_SEC_REACT:
                if close_ < water_mark:
                    water_mark = close_
                    if band == BAND_DNWARD:
                        self.sppt = water_mark

        else: # no known pivot, no defined trend...
            band = BAND_UNKNOWN
            water_mark = close_

        self.last_water_mark = water_mark

        return pandas.Series({ "WM": water_mark, "BAND": band })


class LMKBandCalculatorHeuristic(object):
    def __init__(self, atr_factor=1.0):
        self.atr_factor = atr_factor * 2.0

        self.rsst = 0.0 # rsst => resistent
        self.sppt = 0.0 # sppt => support
        self.last_pivot = None
        self.last_water_mark = None

    def __call__(self, tick):
        pass

