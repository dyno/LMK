from datetime import date
import csv
from urllib2 import urlopen, HTTPError

import pandas

import log

## yahoo ##
# http://www.gummy-stuff.org/Yahoo-data.htm
TODAY_YAHOO_URL = "http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=sd1ohgl1vl1c"
def get_quote_today(symbol):
    url = TODAY_YAHOO_URL % symbol
    log.logger.debug("get_quote_today(): '%s'", url)
    try:
        response = urlopen(url)
        reader = csv.reader(response, delimiter=",", quotechar='"')
        for row in reader:
            if row[0] == symbol and row[1] != "N/A":
                #print pandas.to_datetime(row[1]).date(), date.today()
                if pandas.to_datetime(row[1]).date() == date.today():
                    log.logger.info("get_quote_today(): %s => price: %s, updown: %s",
                                    row[0], row[5], row[8].replace(" - ", ", "))
                    return {
                        "Open" : float(row[2]),
                        "High" : float(row[3]),
                        "Low"  : float(row[4]),
                        "Close": float(row[5]),
                        "Volume": int(row[6]),
                        "Adj Close" : float(row[5]),
                        }
    except HTTPError, e:
        log.logger.debug("open '%s' result error.\n%s", url, e)


if __name__ == "__main__":
    import logging

    from common import probe_proxy

    probe_proxy()
    log.init(logging.DEBUG)

    print get_quote_today("TSLA")
    print get_quote_today("TWTR")

