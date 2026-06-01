# AcquireML — Developer shortcuts
# Usage: make <target>   e.g.  make run   or   make compare
#
# Python interpreter — uses whatever 'python3' is on your PATH by default.
# Override for a specific version:  PYTHON=/usr/bin/python3.11 make test

PYTHON ?= python3

.PHONY: install run compare compare-cip explore explain recommend test clean

## install      — install the package and all dependencies
install:
	$(PYTHON) -m pip install -e ".[dev]"

## run          — run the active learning engine (AZM target, 10 iterations)
run:
	$(PYTHON) -m acquireml.cli \
		--antibiotic azm \
		--iterations 10 \
		--initial-pool 10 \
		--batch-size 25

## compare      — AL vs Random Sampling learning curve chart (Azithromycin)
compare:
	$(PYTHON) -m acquireml.compare \
		--antibiotic azm \
		--iterations 15 \
		--runs 5 \
		--batch-size 25 \
		--output learning_curve.png

## compare-cip  — AL vs Random Sampling learning curve chart (Ciprofloxacin)
compare-cip:
	$(PYTHON) -m acquireml.compare \
		--antibiotic cip \
		--iterations 15 \
		--runs 5 \
		--batch-size 50 \
		--output cip_learning_curve.png

## explore      — generate the 4-panel dataset overview chart
explore:
	$(PYTHON) -m acquireml.explore \
		--data-dir data \
		--output data_overview.png

## explain      — rank DNA fragments by predictive importance (AZM default)
explain:
	$(PYTHON) -m acquireml.explain \
		--antibiotic azm \
		--top-n 20 \
		--output azm_importance.png

## recommend    — rank new unlabeled strains by experimental priority
##               Edit --input-file to point at your CSV of new strains
recommend:
	$(PYTHON) -m acquireml.recommend \
		--antibiotic azm \
		--input-file YOUR_STRAINS.csv \
		--top-n 20

## test         — run the full test suite
test:
	$(PYTHON) -m pytest tests/ -v

## clean        — remove generated chart and output files
clean:
	rm -f learning_curve.png cip_learning_curve.png \
	      data_overview.png azm_importance.png cip_importance.png \
	      recommendations.csv
