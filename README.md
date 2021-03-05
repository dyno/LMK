## LMK

> *LMK* means "Livermore Market Key" which is defined in [Jesse Livermore](https://en.wikipedia.org/wiki/Jesse_Lauriston_Livermore)'s book "HOW TO TRADE IN STOCKS: The Livermore Formula for Combining Time Element and Price".
> If you happend to have read the book, it might also be interesting to read <http://blog.dynofu.me/post/2014/07/26/jesse-livermore-market-method.html>

## Does it still work?
* <http://blessedfool.blogspot.com/2013/05/project-freedom-12-livermore-secret.html>
* TODO: backtest with zipline


## Get Started with the code


- Cell 1 - configure matplotlib

```python
%matplotlib inline

import matplotlib
matplotlib.rcParams['figure.figsize'] = (19, 8)
matplotlib.rcParams['font.family'] = 'Hei'
```

- Cell 2 - run it...

```python
from lmk.ticker import Ticker

ticker = Ticker("TSLA")
ticker.retrieve_history("2015-06-01", "2016-04-30")
ticker.visualize("V,C,CL,LMK,WM,PV")
```

and github renders ```ipynb``` files, so here is what the above looks like.
<https://github.com/dyno/LMK/blob/master/lmk.ipynb>

## File Layout

```
.
├── README.md
├── book
│   ├── 1938_1940.py
│   └── 1938_1940.txt
├── lmk
│   ├── __init__.py
│   ├── cache.py
│   ├── calculator
│   │   ├── ATRCalculator.py
│   │   ├── EntryPointCalculator.py
│   │   ├── LMKBandCalculator.py
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
│   ├── test
│   │   ├── __init__.py
│   │   ├── test_calculator.py
│   │   ├── test_datasource.py
│   │   ├── test_market.py
│   │   └── test_utils.py
│   ├── ticker.py
│   └── utils.py
├── run.md
├── Makefile
└── scripts
    ├── launchd_wrapper.sh
    ├── org.jupyter.server.plist
    └── run_docker.sh
```


### Code Highlight ###

* ```NetEase.py``` - Get China market data with better quality than Yahoo/Google.
* ```PivotCalculator.py``` - An algorithm to calculate local crest/trough.


## TODO List

* multi-tickers in one graph (unlikely...)

* zipline ...

* ~~the cache layer~~ see Market.py/cache.py

