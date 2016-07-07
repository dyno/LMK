```python
>>> # http://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-matplotlib
... %matplotlib inline
...
>>> # http://matplotlib.org/users/customizing.html
... import matplotlib
>>> matplotlib.rcParams['figure.figsize'] = (19, 8)
>>> # matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
... matplotlib.rcParams['font.sans-serif'] = ['STFangsong']
...
>>> # http://stackoverflow.com/questions/11707586/python-pandas-widen-output-display
... import pandas
>>> pandas.set_option('display.max_columns', 500)
>>> pandas.set_option('display.width', 200)
```

```python
>>> import logging
>>> from datetime import timedelta
...
>>> import lmk.ticker
>>> from imp import reload
>>> reload(lmk.calculator.LMKBandCalculator)
>>> reload(lmk.ticker)
...
>>> from lmk.ticker import Ticker
>>> from lmk.utils import env
>>> env.logger.setLevel(logging.DEBUG)
/Users/dyno/.pyenv/versions/3.5.1/envs/inotebook3/lib/python3.5/site-packages/matplotlib/font_manager.py:273: UserWarning: Matplotlib is building the font cache using fc-list. This may take a moment.
  warnings.warn('Matplotlib is building the font cache using fc-list. This may take a moment.')
/Users/dyno/.pyenv/versions/3.5.1/envs/inotebook3/lib/python3.5/site-packages/matplotlib/font_manager.py:273: UserWarning: Matplotlib is building the font cache using fc-list. This may take a moment.
  warnings.warn('Matplotlib is building the font cache using fc-list. This may take a moment.')
```

```python
>>> stk = Ticker("TSLA")
...
>>> end = env._today
>>> #end = (env.today - timedelta(1)).strftime("%Y-%m-%d")
... #stk.retrieve_history("2016-02-01", end, freq="W-MON")
... stk.retrieve_history("2016-02-01", end, freq="D")
...
>>> #stk.visualize("V,C,HLC,BANDL,WM,PV,PVL,EE,ODR", ylimits=(140,300))
... stk.visualize("V,C,BAND,WM,PV,ODR,EE", ylimits=(140,300))
>>> stk.visualize("V,C,CL,HLC", ylimits=(140,300))
DEBUG|Yahoo.py:30#get_quote_today()# url = 'http://download.finance.yahoo.com/d/quotes.csv?s=TSLA&f=sd1ohgl1vl1c'
 INFO|Yahoo.py:37#get_quote_today()# TSLA => price: 215.94, updown: +1.50, +0.70%
```

```python
>>> stk = Ticker("000001.SS")
>>> stk.retrieve_history("2015-02-01", "2015-12-01")
>>> stk.visualize("V,C,LMK,WM,PV,EE,ODR", ylimits=(2500,5200))
```
