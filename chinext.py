#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import urllib2
import sys
import pickle
from os.path import exists, join
from HTMLParser import HTMLParser

## globals ##
db = None

##
class MyHTMLParser(HTMLParser):
    def __init__(self, *argv, **kargs):
        HTMLParser.__init__(self, *argv, **kargs)
        self.head_passed = False
        self.entry_start = False

        self.td_count = 0
        self.db = {}
        self.symbol = None
        self.name = ""
        self.ipo_date = ""

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            if self.head_passed:
                self.entry_start = True
                self.td_count = 0

        if tag == "td":
            self.td_count += 1

    def handle_endtag(self, tag):
        if tag == "tr":
            self.entry_start = False
            if self.head_passed:
                self.db[self.symbol] = (self.symbol, self.name, self.ipo_date)

            self.head_passed = True

#1		<td class="bg1"><strong>证券代码</strong></td>
#2		<td class="bg1"><strong>申购代码</strong></td>
#3		<td class="bg1"><strong>证券简称</strong></td>
#4		<td class="bg1"><strong>网上发行日</strong></td>
#5		<td class="bg1"><strong>上市日</strong></td>
#6		<td class="bg1"><strong>发行量(万股)</strong></td>
#7		<td class="bg1"><strong>网上发行量(万股)</strong></td>
#8		<td class="bg1"><strong>申购上限(万股)</strong></td>
#9		<td class="bg1"><strong>发行价(元)</strong></td>
#10		<td class="bg1"><strong>市盈率</strong></td>
#11		<td class="bg1"><strong>总冻结资金(亿元)</strong></td>
#12		<td class="bg1"><strong>中签率</strong></td>
#13		<td class="bg1"><strong>中签号</strong></td>
    def handle_data(self, data):
        if self.entry_start:
            data = data.strip()
            if data:
                if self.td_count == 1:      # 申购代码
                    self.symbol = data
                elif self.td_count == 3:    # 证券简称
                    self.name = data
                elif self.td_count == 5:    # 上市日
                    self.ipo_date = data


def get_chinext_db():
    global db
    if not db is None: return db

    db_file = join("cache", "chinext.db")
    if exists(db_file):
        db = pickle.load(open(db_file))
        return db

    url = "http://quotes.money.163.com/f10/gemNewListing.html"
    f = urllib2.urlopen(url)
    #f = open("gemNewListing.html")
    parser = MyHTMLParser()
    parser.feed(f.read())
    db = parser.db
    pickle.dump(db, open(db_file, "wb"))

    return db

if __name__ == "__main__":
    from common import probe_proxy
    probe_proxy()

    db = get_chinext_db()
    print db

