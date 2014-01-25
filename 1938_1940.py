import pylab
pylab.rcParams['figure.figsize'] = (20.0, 10.0)

import re
import pandas as pd
import numpy as np
from numpy import ma

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
df = pd.DataFrame(index=dates, columns=("US_band", "US_price", "US_pivotal",
                                        "BS_band", "BS_price", "BS_pivotal",
                                        "Key_band", "Key_price", "Key_pivotal"))

#1938/01/01   NN65.75*, UP 57*,    UD 122.75*
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
            US_band, US_price, US_pivotal, \
            BS_band, BS_price, BS_pivotal, \
            Key_band, Key_price, Key_pivotal = m.groups()
            df.loc[date] = (int(band_dict[US_band]) if US_band else np.nan, float(US_price) if US_price else np.nan, True if US_pivotal else False,
                            int(band_dict[BS_band]) if BS_band else np.nan, float(BS_price) if BS_price else np.nan, True if BS_pivotal else False,
                            int(band_dict[Key_band]) if Key_band else np.nan, float(Key_price) if Key_price else np.nan, True if Key_pivotal else False)

df.dropna(axis=0, how="all", inplace=True)

## validat ##
def validate(row):
    if not (pd.isnull(row["US_price"]) or pd.isnull(row["BS_price"]) or pd.isnull(row["Key_price"])):
        if row["US_price"] + row["BS_price"] != row["Key_price"]:
            print row.name

df.apply(validate, axis=1)

## plot ##
style_dict = {
            DD : "rv",
            NN : "m>",
            SN : "m*",
            SY : "c*",
            NY : "c<",
            UD : "g^",
        }

for idx, name in enumerate(["Key", "US", "BS"]):
    price = df["%s_price" % name]
    band = df["%s_band" % name]
    pivotal = df["%s_pivotal" % name]
    alpha = 1.0 - idx * .3

    ax = plt.gca()
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

    # pivotal
    mask = ma.make_mask(df.index)
    mask = ma.masked_where(pivotal == True, mask)
    chosen = ma.masked_where(~mask.mask, price)
    plt.plot(df.index, chosen, "bo", alpha=.3 * alpha)

plt.show()
