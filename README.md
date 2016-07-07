## LMK

> *LMK* means "Livermore Market Key" which is defined in Jesse Livermore's book "HOW TO TRADE IN STOCKS: The Livermore Formula for Combining Time Element and Price".  <https://en.wikipedia.org/wiki/Jesse_Lauriston_Livermore>
> <http://blog.dynofu.me/post/2014/07/26/jesse-livermore-market-method.html>

## Does it still work?
* <http://blessedfool.blogspot.com/2013/05/project-freedom-12-livermore-secret.html>
* TODO: backtest with zipline


## Get Started with the code

```python
from lmk.ticker import Ticker

ticker = Ticker("TSLA")
ticker.retrieve_history("2015-06-01", "2016-04-30")
ticker.resample_history(freq="D")
ticker.visualize("V,C,CL,LMK,WM,PV")
```


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
├── run_test.sh
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

* --the cache layer-- see Market.py/cache.py

* --Chinese font (on Mac)--

```
# remove font cache
# rm -rf $(python -c "import matplotlib; print(matplotlib.get_cachedir())")

# list all available fonts.
from matplotlib.font_manager import FontManager
m = FontManager()
{f.name:f.fname for f in m.ttflist}

# pick a font.
matplotlib.rcParams['font.family'] = ['sans-serif']
matplotlib.rcParams['font.sans-serif'] = ['STHeiti']
```
