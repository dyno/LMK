#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import re
from operator import gt, lt
from datetime import datetime, date, timedelta
from collections import namedtuple

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.dates import num2date
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY, FRIDAY

import pandas
from numpy import ma, nan
from dateutil.relativedelta import relativedelta, MO, TH

from lmk.market.China import China
from lmk.market.US import US
from lmk.calculator.ATRCalculator import ATRCalculator
from lmk.calculator.EntryPointCalculator import EntryPointCalculator, BUY, SELL
from lmk.calculator.ODRCalculator import ODRCalculator
from lmk.calculator.PivotCalculator import PivotCalculator
#from lmk.calculator.LMKBandCalculator import LMKBandCalculatorHeuristic as LMKBandCalculator
from lmk.calculator.LMKBandCalculator import LMKBandCalculatorPivot as LMKBandCalculator
from lmk.calculator.LMKBandCalculator import BAND_UPWARD, BAND_NAT_RALLY, BAND_SEC_RALLY, \
                                             BAND_SEC_REACT, BAND_NAT_REACT, BAND_DNWARD, BAND_UNKNOWN
from lmk.utils import env

import warnings
from pandas.core.common import SettingWithCopyWarning
warnings.simplefilter('error',SettingWithCopyWarning)

pandas.set_option('display.max_columns', 500)
pandas.set_option('display.width', 200)
plt.rcParams['figure.figsize'] = (19, 6)
# http://www.vartang.com/2014/04/matplotlib-plot/
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']


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

    def process_history(self, freq="D", pivot_window_size=5, atr_factor=1.0):
        h = self.history

        # without .copy(), you will get SettingWithCopyWarning somewhere ...
        h = h[h["Volume"] != 0].copy()

        # ** ATR ** => Average True Range
        c = ATRCalculator(window_size=20)
        h["ATR"] = h.apply(c, axis=1)
        h.fillna(method="backfill", axis=0, inplace=True)

        if freq != "D":
            resampled = pandas.DataFrame(h["Close"].resample(freq, how="last"), columns=("Close",))
            resampled["Open"] = h["Open"].resample(freq, how="first")
            resampled["High"] = h["High"].resample(freq, how="max")
            resampled["Low"] = h["Low"].resample(freq, how="min")
            resampled["Volume"] = h["Volume"].resample(freq, how="sum")
            assert "ATR" in h.columns, "ATR needs to be processed in daily data!"
            resampled["ATR"] = h["ATR"].resample(freq, how="last")

            self.history = resampled
            h = self.history

        # e.g. the spring festival week
        dropped = h.dropna(axis=0, inplace=True)
        if dropped is not None:
            env.logger.debug("NA dropped: %s" % dropped)

        # ** ODR ** => One Day Reversal
        c = ODRCalculator()
        h["ODR"] = h.apply(c, axis=1)

        # ** Pivot ** => Local peaks and valleys. Pivot points is necessary to calculate band
        c = PivotCalculator(window_size=pivot_window_size, cmp=gt)
        h["Close"].apply(c)
        h["Top"] = c.result
        c = PivotCalculator(window_size=pivot_window_size, cmp=lt)
        h["Close"].apply(c)
        h["Btm"] = c.result

        # ** EntryPoint ** => Entry/Exit
        c = EntryPointCalculator(trade_type=BUY, atr_factor=atr_factor)
        h["Buy"] = h.apply(c, axis=1)
        c = EntryPointCalculator(trade_type=SELL, atr_factor=atr_factor)
        h["Sell"] = h.apply(c, axis=1)

        # necessary to calculate updown
        h["CC"] = h["Close"].pct_change()
        h.fillna(method="backfill", axis=0, inplace=True)

        # ** LMK ** => Livermore Market Key
        c = LMKBandCalculator(atr_factor=atr_factor)
        band_watermark = h.apply(c, axis=1)
        #h = pandas.merge(h, band_watermark, left_index=True, right_index=True, sort=False)
        h["WM"] = band_watermark["WM"]
        h["BAND"] = band_watermark["BAND"]

        self.history = h

    def visualize(self, components="C,CL,HLC,BAND,BANDL,WM,PV,PVL,ODR,EE,BS", fluct_factor=.5):
        components = re.split("[-:,;.]", components)
        h = self.history

        #-----------------------------------------------------------------------
        ax0 = plt.subplot2grid((5,1), (0, 0), rowspan=4)
        ax0.set_xmargin(0.02)
        #http://stackoverflow.com/questions/3305865/what-is-the-difference-between-log-and-symlog
        #ax0.set_yscale("symlog", linthreshy=30)
        ax1 = plt.subplot2grid((5,1), (4, 0), rowspan=1, sharex=ax0)
        ax1.yaxis.set_visible(False)
        #ax1.set_yscale("symlog", linthreshy=1000)
        figure = plt.gcf()
        figure.suptitle("%s%s" % (self.symbol, "" if self.symbol == self.name else ("(%s)" % self.name)))
        figure.subplots_adjust(hspace=0)

        min_close = min(h["Close"])
        max_close = max(h["Close"])
        height = min_close * fluct_factor
        ymin =  min_close * 0.98
        ymax = min_close + (height * 1.02)
        if ymax < max_close:
            height = max_close - min_close
            ymax = min_close + height * 1.02
        ax0.set_ylim(ymin, ymax)

        ax0.set_axis_bgcolor('white')
        ax1.set_axis_bgcolor('white')


        #-----------------------------------------------------------------------
        # Basic price line
        if "CL" in components: # Close Line
            ax0.plot(h.index, h["Close"], "-", color="black", alpha=0.5)

        # Water Mark
        if "WM" in components:
            r = h.query("WM > 0")
            ax0.plot(r.index, r["WM"], "c-", drawstyle="steps-post", alpha=1.0)

        # Pivots, major Trend
        pivots = h.query("Top == True or Btm == True")

        if "PVL" in components: # pivot line
            ax0.plot(pivots.index, pivots["Close"], "-", color="blue", alpha=.3)
            rs = h[h["Top"]]
            ax0.plot(rs.index, rs["Close"], "g^", alpha=1.0)
            rs = h[h["Btm"]]
            ax0.plot(rs.index, rs["Close"], "rv", alpha=1.0)

        if "PV" in components: # pivot label
            for x, tick in pivots.iterrows():
                if tick["Top"]:
                    y = tick["High"]
                else:
                    y = tick["Low"]
                s = "%.2f" % tick["Close"]
                ax0.text(x, y, s, alpha=.5)

        # Basic High/Low/Close/Volume Chart
        # Ups ...
        rs = h.query("CC >= 0")
        # Volume
        ax1.bar(rs.index, rs["Volume"], width=1, color="black", edgecolor="black", linewidth=1, alpha=.3, align="center")
        if "C" in components:
            ax0.plot(rs.index, rs["Close"], "_", color="black", alpha=.5, markeredgewidth=2)
        if "HLC" in components:
            ax0.plot(rs.index, rs["Close"], "_", color="black", alpha=1, markeredgewidth=1)
            rs = h.query("Close >= Open")
            ax0.vlines(rs.index, rs["Low"], rs["High"], color="black", edgecolor="black", alpha=1, linewidth=1)

        # Downs ...
        rs = h.query("CC < 0")
        # Volume
        ax1.bar(rs.index, rs["Volume"], width=1, color="red", edgecolor="red", linewidth=1, alpha=.3, align="center")
        if "C" in components:
            ax0.plot(rs.index, rs["Close"], "_", color="red", alpha=.5, markeredgewidth=2)
        if "HLC" in components:
            ax0.plot(rs.index, rs["Close"], "_", color="red", alpha=1, markeredgewidth=1)
            rs = h.query("Close < Open")
            ax0.vlines(rs.index, rs["Low"], rs["High"], color="red", alpha=1, linewidth=1)

        if "BAND" in components:
            style_dict = {
                BAND_DNWARD     : "rv",
                BAND_NAT_REACT  : "m<",
                BAND_SEC_REACT  : "m*",
                BAND_SEC_RALLY  : "c*",
                BAND_NAT_RALLY  : "c>",
                BAND_UPWARD     : "g^",
            }
            for band in range(BAND_DNWARD, BAND_UPWARD + 1):
                #if band in (BAND_SEC_REACT, BAND_SEC_RALLY): continue
                rs = h.query("WM == Close and BAND == %s" % band)
                ax0.plot(rs.index, rs["Close"], style_dict[band], alpha=1.0)

        if "BANDL" in components:
            # up trend
            mask = ma.make_mask(h.index)
            mask = ma.masked_where(((h["BAND"] >= BAND_NAT_REACT) | (h["EE"] == "B")) & (h["EE"] != "S"), mask)
            chosen = ma.masked_where(~mask.mask, h["Close"])
            if chosen.any():
                ax0.plot(h.index, chosen, "g-", linewidth=1, alpha=1)
            # down trend
            mask = ma.make_mask(h.index)
            mask = ma.masked_where(((h["BAND"] <= BAND_NAT_REACT) | (h["EE"] == "S")) & (h["EE"] != "B"), mask)
            chosen = ma.masked_where(~mask.mask, h["Close"])
            if chosen.any():
                ax0.plot(h.index, chosen, "r-", linewidth=1, alpha=.5)

        # ODR => One Day Reversal
        if "ODR" in components:
            rs = h[h["ODR"]]
            ax0.plot(rs.index, rs["Close"], "rx", markersize=8, markeredgewidth=3, alpha=1)

        # Entry/Exit Points
        if "EE" in components or "BS" in components: # EE: Entry/Exit; BS: Buy/Sell
            rs = h[h["Buy"]]
            ax0.plot(rs.index, rs["Close"], "g+", markersize=8, markeredgewidth=3, alpha=1)
            rs = h[h["Sell"]]
            ax0.plot(rs.index, rs["Close"], "r_", markersize=8, markeredgewidth=3, alpha=1)


        #-----------------------------------------------------------------------
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

