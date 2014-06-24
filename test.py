#!/usr/bin/python
# vim: set fileencoding=utf-8 :

from one import Environment, Stock, PivotCalculator

_env = Environment()
print "Are we using proxy? %s" % ("Yes" if _env.probe_proxy() else "No", )

for symbol in (
               #"^IXIC",
               #"000001.SS",
               #"TSLA",
               "ANET",
               "---",
               "300011.SZ", #鼎汉技术
              ):
    if symbol.startswith("---"): break
    stk = Stock(symbol)
    print "%s => %s" % (symbol, stk.name)
    stk.retrieve_history("2014-01-01", _env._today)
    #stk.retrieve_history("2014-01-01", "2014-05-17")
    #stk.process_history(freq="W-MON")
    stk.process_history(freq="D")
    h = stk.history
    n = 2
    print "head(n)..."
    print h.head(n)
    print "tail(n) ..."
    print h.tail(n)

    #stk.visualize("HLC,BAND,PV,PVL")
    #stk.visualize("PV,PVL", fluct_factor=.15)
    #stk.visualize("HLC,PV,PVL", fluct_factor=.15)
    #stk.visualize("BAND,PV,PVL", fluct_factor=0.2)
    stk.visualize("HLC,PV,PVL,EE,ODR", fluct_factor=0.15)
