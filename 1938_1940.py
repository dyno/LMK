import pylab
pylab.rcParams['figure.figsize'] = (20.0, 10.0)

import sys
import re
import pandas as pd
import numpy as np
from numpy import ma
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY, FRIDAY

UD = 6
NY = 5
SY = 4
SN = 3
NN = 2
DD = 1

band_dict = {"UD":6, "NY":5, "SY":4, "SN":3, "NN":2, "DD":1}

## ETL ##
dates = pd.date_range(start='19380101', end='19400217', freq="D")
df = pd.DataFrame(index=dates, columns=("US_band", "US_price", "US_extreme",
                                        "BS_band", "BS_price", "BS_extreme",
                                        "Key_band", "Key_price", "Key_extreme"))

# e.g. 1938/01/01   NN65.75*, UP 57*,    UD 122.75*
ptn = re.compile(r"""
(\d+/\d+/\d+)\s+                       # DATE
(?:([DNPSUY]{2})\s+([0-9.]+)(\*?))*,   # U.S. STEEL
\s*(?:([DNPSUY]{2})\s+([0-9.]+)(\*?))*,# BETHLEHEM STEEL
\s*(?:([DNPSUY]{2})\s+([0-9.]+)(\*?))* # KEY PRICE
""",re.VERBOSE)
with open("1938_1940.txt") as f:
    for idx, line in enumerate(f):
        m = ptn.search(line)
        if m:
            date, \
            US_band, US_price, US_extreme, \
            BS_band, BS_price, BS_extreme, \
            Key_band, Key_price, Key_extreme = m.groups()
            df.loc[date] = (int(band_dict[US_band]) if US_band else np.nan, float(US_price) if US_price else np.nan, True if US_extreme else False,
                            int(band_dict[BS_band]) if BS_band else np.nan, float(BS_price) if BS_price else np.nan, True if BS_extreme else False,
                            int(band_dict[Key_band]) if Key_band else np.nan, float(Key_price) if Key_price else np.nan, True if Key_extreme else False)

df.dropna(axis=0, how="all", inplace=True)

## Validate ##
def validate(row):
    if not (pd.isnull(row["US_price"]) or pd.isnull(row["BS_price"]) or pd.isnull(row["Key_price"])):
        if row["US_price"] + row["BS_price"] != row["Key_price"]:
            print row.name

df.apply(validate, axis=1)

## Plot ##
style_dict = {
            DD : "rv",
            NN : "m>",
            SN : "m*",
            SY : "c*",
            NY : "c<",
            UD : "g^",
        }

#for idx, name in enumerate(["Key", "US", "BS"]):
plt.suptitle("Livermore Market Method - Map for Anticipating Future Movements")
names = {"US": "U.S. STEEL", "BS": "BETHLEHEM STEEL", "Key": "KEY PRICE"}
price_distances =  {"US": 6, "BS": 6, "Key": 12}
stks = ["US", "BS", "Key"]
for idx, name in enumerate(stks):
    price = df["%s_price" % name]
    band = df["%s_band" % name]
    extreme = df["%s_extreme" % name]
    alpha = 1.0

    #ax = plt.gca()
    ax = plt.subplot(len(stks), 1, idx+1)
    plt.ylabel(names[name])
    ax.set_xmargin(0.02)
    ax.set_ymargin(0.01)

    days = WeekdayLocator(MONDAY)
    months = MonthLocator(range(1, 13), bymonthday=1, interval=1) # every month
    monthsFmt = DateFormatter("%b")
    dayFmt = DateFormatter("%d")
    ax.xaxis.set_major_locator(months)
    ax.xaxis.set_major_formatter(monthsFmt)
    ax.xaxis.set_minor_locator(days)
    ax.grid(True)
    #ax.xaxis.set_minor_formatter(dayFmt)
    ax.xaxis.grid(False, which='major')
    ax.xaxis.grid(True, which='minor')


    for level in range(DD, UD + 1):
        mask = ma.make_mask(df.index)
        mask = ma.masked_where(band == level, mask)
        chosen = ma.masked_where(~mask.mask, price)
        #if chosen.any():
        plt.plot(df.index, chosen, style_dict[level], alpha=alpha)

    # upward trend
    mask = ma.make_mask(df.index)
    mask = ma.masked_where((band == NY) | (band == SY) | (band == UD), mask)
    chosen = ma.masked_where(~mask.mask, price)
    plt.plot(df.index, chosen, "g-", alpha=alpha)

    # downward trend
    mask = ma.make_mask(df.index)
    mask = ma.masked_where((band == NN) | (band == SN) | (band == DD), mask)
    chosen = ma.masked_where(~mask.mask, price)
    plt.plot(df.index, chosen, "r-", alpha=alpha)

    # rally or reaction extreme
    mask = ma.make_mask(df.index)
    mask = ma.masked_where((extreme == True) & (band != UD) & (band != DD), mask)
    chosen = ma.masked_where(~mask.mask, price)
    plt.plot(df.index, chosen, "bo", alpha=.3 * alpha)

    #
    ymin, ymax = plt.ylim()

    # pivotal points
    mask = ma.make_mask(df.index)
    mask = ma.masked_where((extreme == True) & (band == UD), mask)
    chosen = ma.masked_where(~mask.mask, price)
    plt.plot(df.index, chosen, "gd", alpha=.5 * alpha)
    for i, v in price[mask.mask].dropna().iteritems():
        plt.axvline(i, color="g", ymin=(v - ymin - price_distances[name] / 2) / (ymax - ymin),
                    ymax=(v - ymin + price_distances[name] / 2) / (ymax - ymin), alpha=alpha)

    mask = ma.make_mask(df.index)
    mask = ma.masked_where((extreme == True) & (band == DD), mask)
    chosen = ma.masked_where(~mask.mask, price)
    plt.plot(df.index, chosen, "rd", alpha=.5 * alpha)
    for i, v in price[mask.mask].dropna().iteritems():
        plt.axvline(i, color="r", ymin=(v - ymin - price_distances[name] / 2) / (ymax - ymin),
                    ymax=(v - ymin + price_distances[name] / 2) / (ymax - ymin), alpha=alpha)

    #
    plt.axvline(datetime(1938, 1, 1), color="black", alpha=.5, label="1938")
    # the actual data records start ...
    plt.axvline(datetime(1938, 3, 23), color="black", alpha=.7, label="Mar 1938")
    plt.axvline(datetime(1939, 1, 1), color="black", alpha=.5, label="1939")
    plt.axvline(datetime(1940, 1, 1), color="black", alpha=.5,label="1940")
    if name == "BS":
        # "On June 2nd, Bethlehem Steel became a buy at 43" ...
        plt.axvline(datetime(1938, 6, 2), ymax=(43.0-ymin)/(ymax-ymin), label="Jun 2")
    if name == "US":
        #"On the same day U.S. Steel became a buy at 42.1/4" ...
        plt.axvline(datetime(1938, 6, 2), ymax=(42.25-ymin)/(ymax-ymin), label="Jun 2")
    # "On January 4th, the next trend of the market was being indicated" ...
    plt.axvline(datetime(1939, 1, 4), alpha=.3, label="Jan 4")
    # "high price attened in September 1939" ...
    plt.axvline(datetime(1939, 9, 12), alpha=.3, label="Sep 4")
    # "It was not until the middle of January 1940, four months later, that the public was given the facts"...
    plt.axvline(datetime(1940, 1, 11), alpha=.3, label="Sep 4")

plt.show()
