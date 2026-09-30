.PHONY: validate_cases run_eval score analyze make_report all test

SCORED_FILE := $(shell powershell -NoProfile -Command "(Get-ChildItem results/scored/scored_*.csv | Sort-Object LastWriteTime | Select-Object -Last 1).FullName")

validate_cases:
	python scripts/validate_cases.py

run_eval:
	python scripts/run_eval.py

score:
	python scripts/score.py

analyze:
	python scripts/analyze.py "$(SCORED_FILE)"

make_report:
	python scripts/make_report.py "$(SCORED_FILE)"

test:
	python -m pytest tests/ -v

all: validate_cases run_eval score analyze make_report