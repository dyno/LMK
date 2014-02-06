import urllib2
import socket

import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY, FRIDAY

def init_plot():
    ax = plt.gca()
    ax.set_xmargin(0.02)
    ax.set_ymargin(0.02)

def show_plot():
    #days = WeekdayLocator(MONDAY)
    days = WeekdayLocator(FRIDAY)
    months  = MonthLocator(range(1, 13), bymonthday=1, interval=1) # every month
    monthsFmt = DateFormatter("%b%y")
    dayFmt = DateFormatter("%d")

    ax = plt.gca()
    #fig, ax = plt.subplots()
    ax.xaxis.set_major_locator(months)
    ax.xaxis.set_major_formatter(monthsFmt)
    #ax.xaxis.set_minor_locator(days)
    #ax.xaxis.set_minor_formatter(dayFmt)
    ax.grid(True)
    ax.xaxis.grid(True, which='major')
    #ax.xaxis.grid(True, which='minor')

    plt.xticks(rotation=25)

    plt.show()

def probe_proxy():
    use_proxy = False

    with open("/etc/resolv.conf") as resolv:
        for line in resolv:
            if line.find("vmware.com") != -1:
                use_proxy = True

    if not use_proxy:
        proxy_support = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_support)
        urllib2.install_opener(opener)

    return use_proxy

if __name__ == "__main__":
    print probe_proxy()
    try:
        response = urllib2.urlopen("http://www.google.com")
    except Exception, e:
        print e
