.PHONY: setup test build score dashboard study clean

setup:
	python -m pip install -e ".[dev]"
	cd ts && npm install

test:
	python -m pytest

study:
	python scripts/run_study.py

build:
	python -m nocturne build --date 2026-10-27

score:
	python -m nocturne score --date 2026-10-28

dashboard:
	python -m nocturne dashboard --date 2026-10-27

clean:
	rm -rf reports/*.png reports/*.html .pytest_cache
