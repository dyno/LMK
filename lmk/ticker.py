#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import re
import functools
from operator import gt, lt
from datetime import datetime, date, timedelta
from collections import namedtuple

# http://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-matplotlib
#%matplotlib inline

# http://matplotlib.org/users/customizing.html
#import matplotlib
#matplotlib.rcParams['figure.figsize'] = (19, 6)
#matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']

from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.dates import num2date
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY, FRIDAY

# http://stackoverflow.com/questions/11707586/python-pandas-widen-output-display
import pandas
#pandas.set_option('display.max_columns', 500)
#pandas.set_option('display.width', 200)

import warnings
from pandas.core.common import SettingWithCopyWarning
warnings.simplefilter('error',SettingWithCopyWarning)

from numpy import ma, nan
from dateutil.relativedelta import relativedelta, MO, TH

from lmk.market.China import China
from lmk.market.US import US
from lmk.calculator.ATRCalculator import ATRCalculator
from lmk.calculator.EntryPointCalculator import EntryPointCalculator, BUY, SELL
from lmk.calculator.ODRCalculator import ODRCalculator
from lmk.calculator.PivotCalculator import PivotCalculator
from lmk.calculator.LMKBandCalculator import LMKBandCalculatorHeuristic
from lmk.calculator.LMKBandCalculator import LMKBandCalculatorPivot
from lmk.calculator.LMKBandCalculator import (
    BAND_UPWARD, BAND_NAT_RALLY, BAND_SEC_RALLY,
    BAND_SEC_REACT, BAND_NAT_REACT, BAND_DNWARD, BAND_UNKNOWN,
    TREND_UP, TREND_DN, TREND_UNKNOWN)

from lmk.utils import env


# ------------------------------------------------------------------------------
def ensure_columns_exist(h, columns):
    columns = list(set(columns) - set(h.columns))
    if not columns: return h

    # XXX: make it configurable
    pivot_window_size = 5
    atr_factor = 1.0

    if "CC" in columns:
        # necessary to calculate updown
        h["CC"] = h["Close"].pct_change()
        h.fillna(method="backfill", axis=0, inplace=True)

    if "ODR" in columns:
        # ** ODR ** => One Day Reversal
        c = ODRCalculator()
        h["ODR"] = h.apply(c, axis=1)

    if "Top" in columns or "Btm" in columns:
        # ** Pivot ** => Local peaks and valleys. Pivot points is necessary to calculate band
        c = PivotCalculator(window_size=pivot_window_size, cmp=gt)
        h["Close"].apply(c)
        h["Top"] = c.result
        c = PivotCalculator(window_size=pivot_window_size, cmp=lt)
        h["Close"].apply(c)
        h["Btm"] = c.result

    if "Buy" in columns or "Sell" in columns:
        # ** EntryPoint ** => Entry/Exit
        ensure_columns_exist(h, ["Top", "Btm"])
        c = EntryPointCalculator(trade_type=BUY, atr_factor=atr_factor)
        h["Buy"] = h.apply(c, axis=1)
        c = EntryPointCalculator(trade_type=SELL, atr_factor=atr_factor)
        h["Sell"] = h.apply(c, axis=1)

    if "WM" in columns or "Trend" in columns or "Band" in columns:
        # ** LMK ** => Livermore Market Key
#            c = LMKBandCalculatorPivot(atr_factor=atr_factor)
#            df = h.apply(c, axis=1)
#            h["Trend"], h["WM"], h["Band"] = df["Trend"], df["WM"], df["Band"]

        ensure_columns_exist(h, ["Top", "Btm"])
        start_pivot = h[h["Top"] | h["Btm"]].ix[0]
        c = LMKBandCalculatorHeuristic(start_pivot, atr_factor=atr_factor)
        df = h.apply(c, axis=1)
        h["Trend"], h["WM"], h["Band"] = df["Trend"], df["WM"], df["Band"]

    return h


# ------------------------------------------------------------------------------
class Ticker:

    def __init__(self, symbol, ds=None):
        self.symbol = symbol
        if symbol[-3:] in (".SS", ".SZ"):
            self.market = China()
        else:
            self.market = US()

        if ds:
            self.market.set_datasource(ds)

    @property
    def name(self):
        return self.market.get_symbol_name(self.symbol)

    def retrieve_history(self, _start, _end):
        self.history = self.market.retrieve_history(self.symbol, _start, _end)

        return self.history

    def preprocess_history(self, freq="D", atr_factor=1.0):
        h = self.history

        # http://chrisalbon.com/python/pandas_dropping_column_and_rows.html
        h = h[h["Volume"] != 0].copy()

        # ** ATR ** => Average True Range
        c = ATRCalculator(window_size=20)
        h["ATR"] = h.apply(c, axis=1)
        h.fillna(method="backfill", axis=0, inplace=True)

        if freq != "D":
            resampled = pandas.DataFrame(h["Close"].resample(freq).last(), columns=["Close"])
            resampled["Open"] = h["Open"].resample(freq).first()
            resampled["High"] = h["High"].resample(freq).max()
            resampled["Low"] = h["Low"].resample(freq).min()
            resampled["Volume"] = h["Volume"].resample(freq).sum()

            assert "ATR" in h.columns, "ATR needs to be processed in daily data!"
            resampled["ATR"] = h["ATR"].resample(freq).last()

            self.history = resampled
            h = self.history

        # e.g. the spring festival week
        dropped = h.dropna(axis=0, inplace=True)
        if dropped is not None:
            env.logger.debug("NA dropped: %s" % dropped)

        self.history = h

        return self.history

    def visualize(self, elements="C,CL,LMK,PV,PVL,ODR", ylimits=None):
        """
        elements: elements that should be plotted, see below.
        ylimits: range of y axis. e.g. (0, 100)

        { # element and its dependent columns
          # Basic
          "C"       : ["Close",],   # Mark the tick['Close'] value with point.
          "CL"      : ["Close",],   # Mark the tick['Close'] value as a line.
          "HLC"     : ["High", "Low", "Close"], # Plot the HLC values in the tick.

          # Derived
          "ODR"     : ["Open", "High", "Low", "Close", "Volume"],   # One Day Reversal. Mark the ODR ticks.

          "PV"      : ["Close", "Top", "Btm"],  # Label the pivot point value.
          "PVL"     : ["Close", "Top", "Btm"],  # Plot a Line that connects the pivot points.

          "EE"      : ["Buy", "Sell"],  # Mark the idea Buy/Sell point.

          "BAND"    : ["Band", "WM"],   # Mark the point with its current LMK Band Level.
          "BANDL"   : ["Band", "Buy", "Sell"],  # Mark line segment according to its current band level.
          "WM"      : ["Trend", "WM"],  # Mark the current resistant or support line
        }
        """

        h = self.history

        # --------------------------------------------------------------
        # ---- Background and Limits ----

        ax0 = plt.subplot2grid((5,1), (0, 0), rowspan=4)
        ax0.set_xmargin(0.02)
        #http://stackoverflow.com/questions/3305865/what-is-the-difference-between-log-and-symlog
        #ax0.set_yscale("symlog", linthreshy=30)
        ax1 = plt.subplot2grid((5,1), (4, 0), rowspan=1, sharex=ax0)
        ax1.yaxis.set_visible(False)
        #ax1.set_yscale("symlog", linthreshy=1000)

        self.figure = plt.gcf()
        #self.figure.clear()
        self.figure.suptitle("%s%s" % (self.symbol, "" if self.symbol == self.name else ("(%s)" % self.name)))
        self.figure.subplots_adjust(hspace=0)

        if ylimits is not None:
            ax0.set_ylim(*ylimits)
        else:
            close_min = min(h["Close"])
            close_max = max(h["Close"])
            height = close_min * .5
            ymin =  close_min * 0.98
            ymax = close_min + (height * 1.02)
            if ymax < close_max:
                height = close_max - close_min
                ymax = close_min + height * 1.02
            ax0.set_ylim(ymin, ymax)

        ax0.set_axis_bgcolor('white')
        ax1.set_axis_bgcolor('white')

        # --------------------------------------------------------------

        # http://stackoverflow.com/questions/1166118/how-to-strip-decorators-from-a-function-in-python
        def plot_elements(*names):
            def decorated(f):

                @functools.wraps(f)
                def wrapper(*argv, **kargs):
                    return f(*argv, **kargs)

                wrapper.elements = names
                return wrapper

            return decorated

        def columns(*names):
            def decorated(f):

                @functools.wraps(f)
                def wrapper(*argv, **kargs):
                    h = argv[1]
                    ensure_columns_exist(h, names)

                    return f(*argv, **kargs)

                return wrapper

            return decorated


        # -- Basic Volume/Price --
        @plot_elements("V")
        @columns("CC", "Volume")
        def plot_V(ax, h):
            up = h[h["CC"] >= 0]
            ax.bar(up.index, up["Volume"], width=1, color="black", edgecolor="black", linewidth=1, alpha=.3, align="center")
            dn = h[h["CC"] < 0]
            ax.bar(dn.index, dn["Volume"], width=1, color="red", edgecolor="red", linewidth=1, alpha=.3, align="center")

        @plot_elements("C")
        @columns("Close", "CC")
        def plot_C(ax, h):
            up = h[h["CC"] >= 0]
            ax.plot(up.index, up["Close"], "_", color="black", alpha=.5, markeredgewidth=2)
            dn = h[h["CC"] < 0]
            ax0.plot(dn.index, dn["Close"], "_", color="red", alpha=.5, markeredgewidth=2)

        @plot_elements("CL")
        @columns("Close")
        def plot_CL(ax, h):
            ax.plot(h.index, h["Close"], "-", color="black", alpha=0.5)

        @plot_elements("HLC")
        @columns("High", "Low", "Close", "CC")
        def plot_HLC(ax, h):
            up = h[h["CC"] >= 0]
            ax.plot(up.index, up["Close"], "_", color="black", alpha=1, markeredgewidth=1)
            up = h[h["Close"] >= h["Open"]]
            ax.vlines(up.index, up["Low"], up["High"], color="black", edgecolor="black", alpha=1, linewidth=1)

            dn = h[h["CC"] < 0]
            ax.plot(dn.index, dn["Close"], "_", color="red", alpha=1, markeredgewidth=1)
            dn = h[h["Close"] < h["Open"]]
            ax.vlines(dn.index, dn["Low"], dn["High"], color="red", edgecolor="red", alpha=1, linewidth=1)

        # -- ODR --
        @plot_elements("ODR")
        @columns("ODR", "Close")
        def plot_ODR(ax, h):
            r = h[h["ODR"]]
            ax.plot(r.index, r["Close"], "rx", markersize=8, markeredgewidth=3, alpha=1)

        # -- Pivots --
        @plot_elements("PV")
        @columns("Top", "Btm", "Close", "Low", "High")
        def plot_PV(ax, h):
            pivots = h[h["Top"] | h["Btm"]]
            for x, tick in pivots.iterrows():
                label = "%.2f" % tick["Close"]
                if tick["Top"]: # crest
                    y = tick["High"]
                    ax.text(x, y, label, color="g", alpha=.8)
                else:           # trough
                    y = tick["Low"]
                    ax.text(x, y, label, color="r", alpha=.8)

        @plot_elements("PVL")
        @columns("Top", "Btm", "Close")
        def plot_PVL(ax, h):
            pivots = h[h["Top"] | h["Btm"]]
            ax.plot(pivots.index, pivots["Close"], "-", color="blue", alpha=.3)
            r = h[h["Top"]]
            ax.plot(r.index, r["Close"], "g^", alpha=1.0)
            r = h[h["Btm"]]
            ax.plot(r.index, r["Close"], "rv", alpha=1.0)

        # -- LMK --
        BAND_STYLE_MAP = {
            BAND_DNWARD     : "rv",
            BAND_NAT_REACT  : "m<",
            BAND_SEC_REACT  : "m*",
            BAND_SEC_RALLY  : "c*",
            BAND_NAT_RALLY  : "c>",
            BAND_UPWARD     : "g^",
        }

        @plot_elements("BAND", "LMK")
        @columns("Close", "WM", "Band")
        def plot_BAND(ax, h):
             for band in range(BAND_DNWARD, BAND_UPWARD + 1):
                #if band in (BAND_SEC_REACT, BAND_SEC_RALLY): continue
                r = h[h["WM"] == h["Close"] & h["Band"] == band]
                ax0.plot(r.index, r["Close"], BAND_STYLE_MAP[band], alpha=1.0)

        @plot_elements("BANDL")
        @columns("Band", "Buy", "Sell", "Close")
        def plot_BANDL(ax, h):
            chosen = ma.masked_where(~(h["Band"] >= BAND_NAT_REACT | h["Buy"]), h["Close"])
            if chosen.any():
                ax.plot(h.index, chosen, "g-", linewidth=1, alpha=1)

            chosen = ma.masked_where(~(h["Band"] <= BAND_NAT_REACT | h["Sell"]), h["Close"])
            if chosen.any():
                ax.plot(h.index, chosen, "r-", linewidth=1, alpha=1)

        @plot_elements("WM")
        @columns("Trend", "WM")
        def plot_WM(ax, h):
            chosen = ma.masked_where(~(h['Trend'] == TREND_UP), h["WM"])
            ax.plot(h.index, chosen, drawstyle="steps-post", color="g")
            chosen = ma.masked_where(~(h['Trend'] == TREND_DN), h["WM"])
            ax.plot(h.index, chosen, drawstyle="steps-post", color="r")

        @plot_elements("EE", "BS")
        @columns("Buy", "Sell", "Close")
        def plot_EE(ax, h):
            r = h[h["Buy"]]
            ax0.plot(r.index, r["Close"], "g+", markersize=8, markeredgewidth=3, alpha=1)
            r = h[h["Sell"]]
            ax0.plot(r.index, r["Close"], "r_", markersize=8, markeredgewidth=3, alpha=1)


        # Build the plotting function map ...
        plot_functions = [f for f in locals().values() if callable(f) and hasattr(f, "elements")]
        plot_dict = {}
        for f in plot_functions:
            for element in f.elements:
                plot_dict[element] = f

        # do the real plotting ...
        l = re.split("[-:,;.]", elements)
        for c in l:
            _plot = plot_dict[c]
            if c != "V":
                _plot(ax0, h)
            else:
                _plot(ax1, h)

        # --------------------------------------------------------------
        # ---- Axis and Grid ----

        days = WeekdayLocator(MONDAY)
        #days = WeekdayLocator(FRIDAY)

        #dayFmt = DateFormatter("%d")
        def _dayFmt(x, pos):
            dt = num2date(x)
            return dt.strftime("%d")[-1] if dt.day < 10 else dt.strftime("%d")
        dayFmt = FuncFormatter(_dayFmt)

        months  = MonthLocator(range(1, 13), bymonthday=1, interval=1)
        # http://stackoverflow.com/questions/11623498/date-formatting-with-matplotlib
        def _monthFmt(x, pos):
            dt = num2date(x)
            return dt.strftime('\n%Y') if dt.month == 1 else dt.strftime("\n%b")
        monthFmt = FuncFormatter(_monthFmt)

        for ax in (ax0, ax1):
            ax.xaxis.set_major_locator(months)
            ax.xaxis.set_major_formatter(monthFmt)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color="blue")
            if len(ax.get_xticks()) <= 12:
                ax.xaxis.set_minor_locator(days)
                ax.xaxis.set_minor_formatter(dayFmt)

        ax0.xaxis.grid(True, which='major', color="blue", linestyle="-", alpha=1)
        ax0.xaxis.grid(True, which='minor', color="gray", linestyle="-", alpha=.5)
        ax0.tick_params(labelbottom="off", which="both")
        ax0.yaxis.grid(True)

        ax1.xaxis.grid(True, which='major', color="blue", linestyle="-", alpha=1)
        ax1.xaxis.grid(True, which='minor', color="gray", linestyle="-", alpha=.3)

        # http://stackoverflow.com/questions/12750355/python-matplotlib-figure-title-overlaps-axes-label-when-using-twiny
        #ax0.set_title("%s%s" % (self.symbol, "" if self.symbol == self.name else ("(%s)" % self.name)), y=0.9)

        plt.show()

