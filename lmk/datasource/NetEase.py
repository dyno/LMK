# vim: set fileencoding=utf-8 :

import re
import json
from urllib.error import HTTPError
from io import StringIO
from html.parser import HTMLParser

import requests
import pandas
from pandas import to_datetime

from .DataSource import DataSource
from ..utils import Singleton, env
from ..market.Market import Market


@Singleton
class NetEase(DataSource):
    def _code7(self, symbol):
        if symbol.endswith(".SS"):
            code7 = "0%s" % symbol[:6]
        elif symbol.endswith(".SZ"):
            code7 = "1%s" % symbol[:6]
        else:
            raise Exception("No data for symbol '{}'!".format(symbol))

        return code7

    def _codetype_(self, symbol):
        if re.search("\d{6}", symbol):
            code = symbol[:6]
            type_ = "SH" if symbol[-2:] == "SS" else "SZ"
        else:
            code = symbol
            type_ = "US"

        return code, type_

    def _get_symboltype_(self, symbol):
        if symbol.endswith(".SS") and symbol[:3] in ("600", "601", "900"):
            return "stock"
        if symbol.endswith(".SZ") and symbol[:3] in ("000", "200", "002", "300"):
            return "stock"

        return "index"

    # http://quotes.money.163.com/f10/fhpg_000001.html#01d05a
    FHPG_URL = "http://quotes.money.163.com/f10/fhpg_%s.html#01d05a"
    # FHPG => 分红配股
    def get_split_history(self, symbol):
        class MyHTMLParser(HTMLParser):
            def __init__(self, *argv, **kargs):
                HTMLParser.__init__(self, *argv, **kargs)
                self.result = []

                self.in_h1 = False
                self.ds_start = False
                self.in_td = False

            def handle_starttag(self, tag, attrs):
                if tag == "h1":
                    self.ds_start = False
                    self.in_h1 = True

                if tag == "tr":
                    self.td_count = 0

                if tag == "td":
                    self.in_td = True
                    self.td_count += 1

            def handle_endtag(self, tag):
                if tag == "h1":
                    self.in_h1 = False
                if tag == "td":
                    self.in_td = False

            def handle_data(self, data):
                data = data.strip()
                if self.in_h1 and data.find("分红配股") != -1:
                    self.ds_start = True

                # print self.ds_start, self.in_td, data
                if self.ds_start and self.in_td and data:
                    if self.td_count == 3:  # 送股
                        self.record = []
                        self.record.append(data)
                    elif self.td_count == 4:  # 转增
                        self.record.append(data)
                    elif self.td_count == 5:  # 派息
                        self.record.append(data)
                    elif self.td_count == 7:  # 除权除息日
                        self.record.append(data)
                        self.result.append(self.record)

        # -----------------------------------------------------------------------
        code = symbol[:6]
        url = self.FHPG_URL % code
        env.logger.debug("url = '%s'", url)
        try:
            response = requests.get(url)
            data = response.text
            parser = MyHTMLParser()
            parser.feed(data)
            if len(parser.result) > 0:
                return parser.result
        except HTTPError as e:
            env.logger.debug("open '%s' result error.\n%s", url, e)

    # ---------------------------------------------------------------------------
    def adjust_close_price(self, history, split_history):
        # sort by date
        split_history.sort(key=lambda e: e[3], reverse=True)

        history["_Close"] = history["Close"].copy()  # backup
        for stock_dividend, stock_issue, cash_dividend, dt in split_history:
            try:
                stock_dividend = int(stock_dividend)
            except:
                stock_dividend = 0
            try:
                stock_issue = int(stock_issue)
            except:
                stock_issue = 0
            try:
                cash_dividend = float(cash_dividend)
            except:
                cash_dividend = 0

            # split is in future, no adjust is necessary.
            if dt > env._today:
                continue

            def c(r):
                # 1) only account for split, e.g. http://www.znz888.com/stock/history.php?code=sz300011&type=history
                #    10 * stock_price_before = (10 + stock_dividend + stock_issue) * stock_price_after
                #    yahoo seems to have adopt this method too.
                # 2) consider both split and dividend, e.g. google data.
                #    https://www.google.com/finance/historical?cid=9525130&startdate=Apr+1%2C+2014&enddate=Apr+30%2C+2014&num=30&ei=BmGgU9i1KsrniwLM3oCQDg
                #    10 * stock_price_before + cash_dividend = (10 + stock_dividend + stock_issue) * stock_price_after
                return (
                    r["Close"]
                    if r.name.strftime("%Y-%m-%d") >= dt
                    else (r["Close"] * 10 + cash_dividend) / (10 + stock_dividend + stock_issue)
                )

            # hist.loc[hist.index < _dt, ["Adj Close",]] = hist.loc[hist.index < _dt].apply(c, axis=1)
            history["Adj Close"] = history.apply(c, axis=1)
            history["Close"] = history["Adj Close"]

        del history["Close"]
        history.rename(columns=lambda c: c.replace("_", ""), inplace=True)  # restore

    # ---------------------------------------------------------------------------
    HISTORY_DATA_URL = "".join(
        [
            "http://quotes.money.163.com/service/chddata.html?",
            "code=%s&start=%s&end=%s&",
            "fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;VOTURNOVER;VATURNOVER",
        ]
    )

    def retrieve_history(self, symbol, _start, _end):
        start, end = to_datetime(_start), to_datetime(_end)
        code = self._code7(symbol)

        url = self.HISTORY_DATA_URL % (code, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
        try:
            env.logger.debug("url = '%s'", url)
            response = requests.get(url)

            rs = pandas.read_csv(StringIO(response.text), index_col=0, parse_dates=True)
            # 日期,股票代码,名称,收盘价,最高价,最低价,开盘价,前收盘,涨跌额,涨跌幅,成交量,成交金额
            h = rs[["开盘价", "最高价", "最低价", "收盘价", "成交量", "收盘价"]].copy()
            h.columns = Market.HISTORY_COLUMNS

            if self._get_symboltype_(symbol) == "stock":
                split_history = self.get_split_history(symbol)
                if split_history:
                    self.adjust_close_price(h, split_history)

            h.sort_index(ascending=True, inplace=True)  # expect data to be ascending

            return h
        except HTTPError as e:
            env.logger.debug("url = '%s', error:\n%s", url, e)

    # ---------------------------------------------------------------------------
    STOCK_SEARCH_URL = "http://quotes.money.163.com/stocksearch/json.do?count=10&word=%s"

    def get_symbol_name(self, symbol):
        code, type_ = self._codetype_(symbol)

        url = self.STOCK_SEARCH_URL % code
        env.logger.debug("url = '%s'", url)
        try:
            response = requests.get(url)
            data = response.text
            start, end = data.find("(") + 1, data.find(")")
            data = data[start:end]
            data = json.loads(data)
            for stk in data:
                if stk["type"] == type_:
                    return stk["name"]
        except HTTPError as e:
            env.logger.debug("open '%s' result error.\n%s", url, fmt_err_msg(e))

    # ---------------------------------------------------------------------------
    QUOTE_TODAY_URL = "http://api.money.126.net/data/feed/%s,money.api"

    def get_quote_today(self, symbol):
        code = self._code7(symbol)
        url = self.QUOTE_TODAY_URL % code
        env.logger.debug("url = '%s'", url)
        try:
            response = requests.get(url)
            data = response.text
            start, end = data.find("(") + 1, data.find(")")
            data = data[start:end]
            data = json.loads(data)[code]
            rs = {
                "Open": data["open"],
                "High": data["high"],
                "Low": data["low"],
                "Close": data["yestclose"] + data["updown"],
                # 历史数据: 指数(手), 普通股票(股)
                "Volume": data["volume"] if self._get_symboltype_(symbol) == "stock" else data["volume"] / 100,
                "Adj Close": data["yestclose"] + data["updown"],
            }
            env.logger.info(
                "get_quote_today(): %s => price: %.2f, updown: %.2f, %.2f%%",
                symbol,
                rs["Close"],
                data["updown"],
                data["updown"] * 100 / data["yestclose"],
            )
            return rs
        except HTTPError as e:
            env.logger.debug("open '%s' result error.\n%s", url, e)
