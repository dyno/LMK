#!/usr/bin/python
# vim: set fileencoding=utf-8 :

import logging
from datetime import timedelta
from one import Environment, Stock

_env = Environment()
_env.init_log(loglevel=logging.INFO)
_env.init_log(loglevel=logging.DEBUG)
print "Are we using proxy? %s" % ("Yes" if _env.probe_proxy() else "No", )

check_list = True
for symbol in (
               "---",
               "399102.SZ",
               "300011.SZ", #鼎汉技术
               "300150.SZ", #世纪瑞尔
               "-x-",
               "000001.SS",
               "---",
               "600547.SS", #山东黄金
               "300049.SZ", #福瑞医疗
               "000788.SZ", #北大医疗
               "---",
               "^IXIC", "TSLA",
               "GGAL", "SSRI",
               "SINA", "YOKU",
               "AMBA", "HIMX",
               "---"
               "ANET", #"XNET",
               "-x-",
               "WETF#ds=google",
               ):
    if symbol.startswith("--"):
        check_list = False; continue
    if symbol.startswith("-x-"):
        check_list = True; continue
    if not check_list: continue

    hint = {}
    if "#" in symbol:
        symbol, cmt = symbol.split("#")
        for e in cmt.split(","):
            try:
                k,v = e.split("=")
                hint[k] = v
            except:
                pass

    ds = hint.get("ds")
    if ds:
        stk = Stock(symbol, ds=ds)
    else:
        stk = Stock(symbol)

    #print "%s => %s" % (symbol, stk.name)
    end = _env._today
    #end = (_env.today - timedelta(1)).strftime("%Y-%m-%d")
    stk.retrieve_history("2014-01-01", end)
    #stk.process_history(freq="W-MON")
    stk.process_history(freq="D")
    h = stk.history
    print h.tail(2)

    def index(symbol):
        if symbol.startswith("^"): return True
        if symbol.endswith("SS") and symbol.startswith("00"): return True
        if symbol.endswith("SZ") and symbol.startswith("399"): return True
        return False

    fluct_factor = .1 if index(stk.symbol) else .6
    #stk.visualize("HLC,PV,PVL,EE,ODR", fluct_factor=fluct_factor)
    stk.visualize("HLC,PV,PVL,EE,ODR", fluct_factor=fluct_factor)
    #stk.visualize("BAND,BANDL,PV,EE,ODR", fluct_factor=fluct_factor)
    #stk.visualize()

