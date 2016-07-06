#LMK#

what is LMK?
Livermore Market Key

* *LMK* means "Livermore Market Key" which is defined in Jesse Livermore's book "HOW TO TRADE IN STOCKS: The Livermore Formula for Combining Time Element and Price".
  <https://en.wikipedia.org/wiki/Jesse_Lauriston_Livermore>

## Get Started

```python
from lmk.ticker import Ticker

ticker = Ticker("TSLA")
ticker.retrieve_history("2015-06-01", "2016-04-30")
ticker.visualize("CL,PVL,PV")
```

## TODO

* the cache layer
* multi-tickers in one graph
* backtest with zipline


## File Layout

```
.
├── README.md
├── book
│   ├── 1938_1940.py
│   └── 1938_1940.txt
├── cache
├── deps.txt
├── lmk
│   ├── calculator
│   │   ├── ATRCalculator.py
│   │   ├── EntryExitCalculator.py
│   │   ├── LMKCalculator.py
│   │   ├── ODRCalculator.py
│   │   └── PivotCalculator.py
│   ├── datasource
│   │   ├── DataSource.py
│   │   ├── Google.py
│   │   ├── NetEase.py
│   │   └── Yahoo.py
│   ├── market
│   │   ├── China.py
│   │   ├── Market.py
│   │   └── US.py
│   └── utils.py
├── ticker.py
├── run.md
├── run.sh
├── scripts
│   ├── jupyter_notebook.md
│   ├── launchd_wrapper.sh
│   ├── org.jupyter.server.plist
│   ├── run.sh
│   └── run_docker.sh
```
