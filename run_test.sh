#!/bin/bash

set -x

#python -m unittest discover -v
python -m unittest lmk.test.test_calculator
