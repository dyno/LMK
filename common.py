import traceback
import sys
import urllib2
import socket
from StringIO import StringIO

import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY, FRIDAY

def init_plot(width=20, height=10, title=""):
    plt.rcParams['figure.figsize'] = (width, height)
    plt.clf()
    if title: plt.title(title)
    ax = plt.gca()

def show_plot(filename=""):
    days = WeekdayLocator(MONDAY)
    #days = WeekdayLocator(FRIDAY)
    dayFmt = DateFormatter("%m/%d")
    months  = MonthLocator(range(1, 13), bymonthday=1, interval=1) # every month
    monthFmt = DateFormatter("\n\n%b/%Y")
    #years =

    ax = plt.gca()
    #fig, ax = plt.subplots()
    ax.xaxis.set_major_locator(days)
    ax.xaxis.set_major_formatter(dayFmt)
    ax.xaxis.set_minor_locator(months)
    ax.xaxis.set_minor_formatter(monthFmt)
    ax.grid(True)
    ax.xaxis.grid(True, which='major')
    #ax.xaxis.grid(True, which='minor')

    plt.xticks(rotation=25)

    if not filename:
        plt.show()
    else:
        plt.savefig(filename)


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


def fmt_err_msg(e):
    errmsg = "<%s: %s>" % (e.__class__.__name__, e)

    tb = sys.exc_info()[2]
    if tb:
        sio = StringIO()
        try:
            traceback.print_tb(tb, 10, sio)
            errmsg = "%s\nStackTrace:\n%s" % (errmsg, sio.getvalue())
        finally:
            sio.close()

    return errmsg


if __name__ == "__main__":
    try:
        probe_proxy()
        response = urllib2.urlopen("http://www.google.com")
        raise Exception("nothing actually wrong ;)")
    except Exception, e:
        print fmt_err_msg(e)


