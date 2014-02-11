from datetime import date
import csv
from urllib2 import urlopen, HTTPError

import pandas

import log

## yahoo ##
# http://www.gummy-stuff.org/Yahoo-data.htm
TODAY_YAHOO_URL = "http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=sd1ohgl1vl1"
def get_quote_today(symbol):
    url = TODAY_YAHOO_URL % symbol
    log.logger.debug("get_quote_today_yahoo(): '%s'", url)
    try:
        response = urlopen(url)
        reader = csv.reader(response, delimiter=",", quotechar='"')
        for row in reader:
            if row[0] == symbol and row[1] != "N/A":
                #print pandas.to_datetime(row[1]).date(), date.today()
                if pandas.to_datetime(row[1]).date() == date.today():
                    return row
    except HTTPError, e:
        log.logger.debug("open '%s' result error.\n%s", url, e)


if __name__ == "__main__":
    from common import probe_proxy
    probe_proxy()
    log.init()

    print get_quote_today("TSLA")
