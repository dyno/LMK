import matplotlib.pyplot as plt
from matplotlib.dates import MonthLocator, WeekdayLocator, DateFormatter, MONDAY, FRIDAY

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
    ax.set_xmargin(0.05)
    ax.set_ymargin(0.05)

    plt.xticks(rotation=25)

    plt.show()

