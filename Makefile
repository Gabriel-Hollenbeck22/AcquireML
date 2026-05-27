# AcquireML — Developer shortcuts
# Usage: make <target>   e.g.  make run   or   make compare
#
# If 'python3' below points to the wrong version, replace it with the full
# path: /Library/Frameworks/Python.framework/Versions/3.13/bin/python3

PYTHON := /Library/Frameworks/Python.framework/Versions/3.13/bin/python3

.PHONY: install run compare explore test clean

## install   — install the package and all dependencies
install:
	$(PYTHON) -m pip install -e ".[dev]"

## run        — run the active learning engine (AZM target, 10 iterations)
run:
	$(PYTHON) -m acquireml.cli \
		--antibiotic azm \
		--iterations 10 \
		--initial-pool 10 \
		--batch-size 25

## compare    — generate the AL vs Random Sampling learning curve chart
compare:
	$(PYTHON) -m acquireml.compare \
		--antibiotic azm \
		--iterations 15 \
		--runs 5 \
		--batch-size 25 \
		--output learning_curve.png

## explore    — generate the dataset overview chart
explore:
	$(PYTHON) -m acquireml.explore \
		--data-dir data \
		--output data_overview.png

## test       — run the full test suite
test:
	$(PYTHON) -m pytest tests/ -v

## clean      — remove generated chart files
clean:
	rm -f learning_curve.png data_overview.png
