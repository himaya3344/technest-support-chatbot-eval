# TechNest Evaluation Framework

An evaluation pipeline for a TechNest customer-support chatbot. The chatbot is tested against knowledge-base-grounded cases, scored with deterministic rules and an LLM judge, analyzed for failure patterns, and summarized in a Markdown report.

## Setup

Use Python 3.11 or newer in a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set the Gemini API key. Do not commit `.env`:

```text
GEMINI_API_KEY=your_key_here
```

The configured model is `gemini-3.1-flash-lite`. Test cases are stored in `data/test_cases.json`; the knowledge base and system prompt are in `data/`.

## Pipeline

Run these commands from the repository root in order:

```powershell
python scripts/validate_cases.py
python scripts/run_eval.py
python scripts/score.py
python scripts/analyze.py (Get-ChildItem results\scored\scored_*.csv | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
python scripts/make_report.py (Get-ChildItem results\scored\scored_*.csv | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
```

For a pilot run, limit the number of cases:

```powershell
python scripts/run_eval.py --limit 5
```

Use `--resume path\to\run.jsonl` to continue an interrupted evaluation, and `--category adversarial` to run one test category.

Outputs are written to:

- `results/raw/`: raw JSONL chatbot results
- `results/scored/`: rule- and judge-scored CSV files
- `results/metrics/`: metrics, failure tables, and report inputs
- `results/figures/`: generated charts
- `report/report.md`: generated technical report

## Make targets

The equivalent workflow is:

```powershell
make validate_cases
make run_eval
make score
make analyze
make make_report
make all
```

`analyze` and `make_report` select the most recently modified scored CSV. On Windows without `make`, run the Python commands above directly or use a GNU Make installation.

## Reproducibility

Record these fields with every evaluation run:

- Model: `gemini-3.1-flash-lite`
- Judge model: `gemini-3.1-flash-lite`
- Temperature: `0`
- Random seed: `42`
- Runs per case: `3`
- Run date: record the UTC date and timestamp from the generated `run_YYYYMMDD_HHMMSS.jsonl` filename

The evaluation also records latency and token usage in the raw results. API keys are loaded only from environment variables.

## Tests

```powershell
python -m pytest tests/ -v
```
